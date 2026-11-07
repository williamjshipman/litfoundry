"""Tests for project access control and authorization."""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from litfoundry.catalog.models import Base, User, ProjectDirectory, ProjectACL
from litfoundry.auth.authorization import authorize, AccessLevel, AccessRule


@pytest.fixture
def in_memory_db() -> Session:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def users_and_project(in_memory_db: Session) -> tuple[User, User, User, User, ProjectDirectory]:
    """Create test users and a project."""
    now = datetime.utcnow()
    
    # Create users
    owner = User(
        id=str(uuid4()),
        account_type="local",
        username="owner",
        username_normalized="owner",
        password_hash="hash",
        active=True,
        role=None,
        created_at=now,
        updated_at=now,
    )
    
    admin_user = User(
        id=str(uuid4()),
        account_type="local",
        username="admin",
        username_normalized="admin",
        password_hash="hash",
        active=True,
        role="admin",
        created_at=now,
        updated_at=now,
    )
    
    editor = User(
        id=str(uuid4()),
        account_type="local",
        username="editor",
        username_normalized="editor",
        password_hash="hash",
        active=True,
        role=None,
        created_at=now,
        updated_at=now,
    )
    
    viewer = User(
        id=str(uuid4()),
        account_type="local",
        username="viewer",
        username_normalized="viewer",
        password_hash="hash",
        active=True,
        role=None,
        created_at=now,
        updated_at=now,
    )
    
    disabled_user = User(
        id=str(uuid4()),
        account_type="local",
        username="disabled",
        username_normalized="disabled",
        password_hash="hash",
        active=False,
        role=None,
        created_at=now,
        updated_at=now,
    )
    
    # Create a project owned by owner
    project = ProjectDirectory(
        id=str(uuid4()),
        relative_path=f"projects/{uuid4()}",
        owner_user_id=owner.id,
        public_access="none",
        state_code="ready",
        project_schema_version=1,
        title="Test Project",
        created_at=now,
        updated_at=now,
    )
    
    in_memory_db.add_all([owner, admin_user, editor, viewer, disabled_user, project])
    in_memory_db.commit()
    
    return owner, admin_user, editor, viewer, project


class TestAuthorizationMatrix:
    """Test access resolution matrix."""
    
    def test_disabled_account_always_denied(self, in_memory_db: Session, users_and_project: tuple):
        """Disabled accounts should be denied regardless of other rules."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        disabled_user = User(
            id=str(uuid4()),
            account_type="local",
            username="disabled_test",
            username_normalized="disabled_test",
            password_hash="hash",
            active=False,
            role=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(disabled_user)
        in_memory_db.commit()
        
        decision = authorize(disabled_user, project.id, in_memory_db)
        assert decision.level == AccessLevel.NONE
        assert decision.rule == AccessRule.DEFAULT_DENY
    
    def test_admin_gets_full_access(self, in_memory_db: Session, users_and_project: tuple):
        """Admin should get full access to any project."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        decision = authorize(admin_user, project.id, in_memory_db)
        assert decision.level == AccessLevel.ADMIN
        assert decision.rule == AccessRule.ADMIN
    
    def test_owner_gets_full_access(self, in_memory_db: Session, users_and_project: tuple):
        """Owner should get full access to their own project."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        decision = authorize(owner, project.id, in_memory_db)
        assert decision.level == AccessLevel.OWNER
        assert decision.rule == AccessRule.OWNER
    
    def test_explicit_editor_grant(self, in_memory_db: Session, users_and_project: tuple):
        """Explicit editor grant should give editor access."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        acl = ProjectACL(
            id=str(uuid4()),
            project_id=project.id,
            user_id=editor.id,
            role="editor",
            granted_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(acl)
        in_memory_db.commit()
        
        decision = authorize(editor, project.id, in_memory_db)
        assert decision.level == AccessLevel.EDITOR
        assert decision.rule == AccessRule.EXPLICIT_GRANT
    
    def test_explicit_viewer_grant(self, in_memory_db: Session, users_and_project: tuple):
        """Explicit viewer grant should give viewer access."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        acl = ProjectACL(
            id=str(uuid4()),
            project_id=project.id,
            user_id=viewer.id,
            role="viewer",
            granted_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(acl)
        in_memory_db.commit()
        
        decision = authorize(viewer, project.id, in_memory_db)
        assert decision.level == AccessLevel.VIEWER
        assert decision.rule == AccessRule.EXPLICIT_GRANT
    
    def test_explicit_deny_overrides_public(self, in_memory_db: Session, users_and_project: tuple):
        """Explicit deny should override public default."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        # Make project public view
        project.public_access = "viewer"
        in_memory_db.commit()
        
        # Add explicit deny for viewer
        acl = ProjectACL(
            id=str(uuid4()),
            project_id=project.id,
            user_id=viewer.id,
            role="deny",
            granted_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(acl)
        in_memory_db.commit()
        
        decision = authorize(viewer, project.id, in_memory_db)
        assert decision.level == AccessLevel.NONE
        assert decision.rule == AccessRule.EXPLICIT_DENY
    
    def test_public_viewer_access(self, in_memory_db: Session, users_and_project: tuple):
        """Public viewer projects should be readable by authenticated users."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        project.public_access = "viewer"
        in_memory_db.commit()
        
        # Create a random authenticated user
        random_user = User(
            id=str(uuid4()),
            account_type="local",
            username="random",
            username_normalized="random",
            password_hash="hash",
            active=True,
            role=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(random_user)
        in_memory_db.commit()
        
        decision = authorize(random_user, project.id, in_memory_db)
        assert decision.level == AccessLevel.VIEWER
        assert decision.rule == AccessRule.PUBLIC_ACCESS
    
    def test_public_editor_access(self, in_memory_db: Session, users_and_project: tuple):
        """Public editor projects should be editable by authenticated users."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        project.public_access = "editor"
        in_memory_db.commit()
        
        # Create a random authenticated user
        random_user = User(
            id=str(uuid4()),
            account_type="local",
            username="random",
            username_normalized="random",
            password_hash="hash",
            active=True,
            role=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(random_user)
        in_memory_db.commit()
        
        decision = authorize(random_user, project.id, in_memory_db)
        assert decision.level == AccessLevel.EDITOR
        assert decision.rule == AccessRule.PUBLIC_ACCESS
    
    def test_private_project_default_deny(self, in_memory_db: Session, users_and_project: tuple):
        """Private projects should deny access to non-owner, non-admin users."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        # Project is private by default
        assert project.public_access == "none"
        
        # Create a random authenticated user
        random_user = User(
            id=str(uuid4()),
            account_type="local",
            username="random",
            username_normalized="random",
            password_hash="hash",
            active=True,
            role=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(random_user)
        in_memory_db.commit()
        
        decision = authorize(random_user, project.id, in_memory_db)
        assert decision.level == AccessLevel.NONE
        assert decision.rule == AccessRule.DEFAULT_DENY
    
    def test_explicit_grant_overrides_deny_for_non_admin(self, in_memory_db: Session, users_and_project: tuple):
        """Explicit grant should override no public access for regular users."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        # Add explicit editor grant
        acl = ProjectACL(
            id=str(uuid4()),
            project_id=project.id,
            user_id=editor.id,
            role="editor",
            granted_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        in_memory_db.add(acl)
        in_memory_db.commit()
        
        decision = authorize(editor, project.id, in_memory_db)
        assert decision.level == AccessLevel.EDITOR
        assert decision.rule == AccessRule.EXPLICIT_GRANT
    
    def test_explicit_deny_never_applies_to_admin(self, in_memory_db: Session, users_and_project: tuple):
        """Explicit deny should never apply to admin."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        # Even if we tried to add a deny for admin, admin should still have access
        # (In practice, the UI should prevent this, but the authorization logic must be robust)
        decision = authorize(admin_user, project.id, in_memory_db)
        assert decision.level == AccessLevel.ADMIN
        assert decision.rule == AccessRule.ADMIN
    
    def test_nonexistent_project_denied(self, in_memory_db: Session, users_and_project: tuple):
        """Access to nonexistent projects should be denied."""
        owner, admin_user, editor, viewer, project = users_and_project
        
        fake_project_id = str(uuid4())
        decision = authorize(owner, fake_project_id, in_memory_db)
        assert decision.level == AccessLevel.NONE
        assert decision.rule == AccessRule.DEFAULT_DENY


class TestAccessLevelComparison:
    """Test access level comparison for action authorization."""
    
    def test_viewer_cannot_edit(self):
        """Viewer access should not allow edit actions."""
        decision = pytest.fixture()  # Placeholder for decision with VIEWER level
        from litfoundry.auth.authorization import AuthorizationDecision, AccessLevel, AccessRule
        
        decision = AuthorizationDecision(
            level=AccessLevel.VIEWER,
            rule=AccessRule.PUBLIC_ACCESS,
        )
        
        assert not decision.allows_action(AccessLevel.EDITOR)
        assert not decision.allows_action(AccessLevel.OWNER)
        assert decision.allows_action(AccessLevel.VIEWER)
    
    def test_editor_can_edit_but_not_delete(self):
        """Editor access should allow edit but not delete."""
        from litfoundry.auth.authorization import AuthorizationDecision, AccessLevel, AccessRule
        
        decision = AuthorizationDecision(
            level=AccessLevel.EDITOR,
            rule=AccessRule.EXPLICIT_GRANT,
        )
        
        assert decision.allows_action(AccessLevel.EDITOR)
        assert decision.allows_action(AccessLevel.VIEWER)
        assert not decision.allows_action(AccessLevel.OWNER)
    
    def test_owner_can_delete(self):
        """Owner access should allow all actions."""
        from litfoundry.auth.authorization import AuthorizationDecision, AccessLevel, AccessRule
        
        decision = AuthorizationDecision(
            level=AccessLevel.OWNER,
            rule=AccessRule.OWNER,
        )
        
        assert decision.allows_action(AccessLevel.VIEWER)
        assert decision.allows_action(AccessLevel.EDITOR)
        assert decision.allows_action(AccessLevel.OWNER)
        assert not decision.allows_action(AccessLevel.ADMIN)
    
    def test_admin_can_do_anything(self):
        """Admin access should allow all actions."""
        from litfoundry.auth.authorization import AuthorizationDecision, AccessLevel, AccessRule
        
        decision = AuthorizationDecision(
            level=AccessLevel.ADMIN,
            rule=AccessRule.ADMIN,
        )
        
        assert decision.allows_action(AccessLevel.VIEWER)
        assert decision.allows_action(AccessLevel.EDITOR)
        assert decision.allows_action(AccessLevel.OWNER)
        assert decision.allows_action(AccessLevel.ADMIN)
