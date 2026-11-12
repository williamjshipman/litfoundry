"""Login attempt throttling with sliding window and exponential backoff."""

from datetime import datetime, timedelta, timezone
import math

from sqlalchemy.orm import Session

from litfoundry.catalog import LoginThrottle


class ThrottlingPolicy:
    """Represents a throttling policy with configurable limits and backoff."""
    
    def __init__(self, max_attempts: int, window_minutes: int, backoff_base_seconds: float = 1.0, backoff_max_seconds: float = 900):
        """Initialize throttling policy.
        
        Args:
            max_attempts: Maximum attempts allowed in the window
            window_minutes: Duration of sliding window in minutes
            backoff_base_seconds: Initial backoff time in seconds (default 1s)
            backoff_max_seconds: Maximum backoff time in seconds (default 15 min = 900s)
        """
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds
    
    @classmethod
    def from_policy_dict(cls, policy_dict: dict) -> "ThrottlingPolicy":
        """Create policy from dictionary.
        
        Args:
            policy_dict: Dictionary with keys:
                - per_ip_max_attempts: max attempts per IP per window
                - per_identifier_max_attempts: max attempts per identifier per window
                - window_minutes: sliding window duration
                - backoff_base_seconds: initial backoff (default 1)
                - backoff_max_seconds: max backoff (default 900)
        """
        return cls(
            max_attempts=policy_dict.get("per_ip_max_attempts", 10),
            window_minutes=policy_dict.get("window_minutes", 15),
            backoff_base_seconds=policy_dict.get("backoff_base_seconds", 1.0),
            backoff_max_seconds=policy_dict.get("backoff_max_seconds", 900),
        )


class LoginThrottler:
    """Manages login throttling with sliding window and exponential backoff."""
    
    def __init__(self, ip_policy: ThrottlingPolicy, identifier_policy: ThrottlingPolicy):
        """Initialize throttler with separate policies for IP and identifier.
        
        Args:
            ip_policy: Policy for per-IP throttling
            identifier_policy: Policy for per-identifier (username) throttling
        """
        self.ip_policy = ip_policy
        self.identifier_policy = identifier_policy
    
    def calculate_backoff_seconds(self, attempts: int, policy: ThrottlingPolicy) -> float:
        """Calculate exponential backoff based on attempt count.
        
        Formula: base * 2^(max(attempts - max + 1, 0))
        This gives exponential growth starting when max_attempts is reached.
        
        Args:
            attempts: Number of attempts made
            policy: Throttling policy
            
        Returns:
            Backoff time in seconds, capped at policy maximum
        """
        if attempts < policy.max_attempts:
            return 0.0
        
        excess_attempts = attempts - policy.max_attempts + 1
        backoff = policy.backoff_base_seconds * math.pow(2, excess_attempts - 1)
        return min(backoff, policy.backoff_max_seconds)
    
    def check_throttle(self, session: Session, ip_address: str, identifier: str = None, is_admin: bool = False) -> dict:
        """Check if login should be throttled.
        
        Returns a dictionary with:
        - throttled: bool - True if should be throttled
        - retry_after_seconds: int or None - seconds to wait if throttled
        
        Args:
            session: SQLAlchemy session
            ip_address: Client IP address
            identifier: Username/identifier (None for admin check per-IP only)
            is_admin: True if admin account (skip per-identifier check)
            
        Returns:
            dict with throttle state
        """
        now = datetime.now(timezone.utc)
        result = {"throttled": False, "retry_after_seconds": None}
        
        # Check IP throttle
        ip_key = f"ip:{ip_address}"
        ip_throttle = session.query(LoginThrottle).filter_by(key=ip_key).first()
        
        ip_attempts = 0
        ip_backoff = 0
        
        if ip_throttle:
            # Ensure expires_at is timezone-aware for comparison
            expires_at = ip_throttle.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at > now:
                ip_attempts = ip_throttle.attempts
                ip_backoff = self.calculate_backoff_seconds(ip_attempts, self.ip_policy)
                if ip_backoff > 0:
                    result["throttled"] = True
                    result["retry_after_seconds"] = int(math.ceil(ip_backoff))
                    return result
        
        # Check per-identifier throttle (skip for admin)
        if not is_admin and identifier:
            identifier_key = f"id:local:{identifier.lower().strip()}"
            id_throttle = session.query(LoginThrottle).filter_by(key=identifier_key).first()
            
            id_attempts = 0
            id_backoff = 0
            
            if id_throttle:
                # Ensure expires_at is timezone-aware for comparison
                expires_at = id_throttle.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                
                if expires_at > now:
                    id_attempts = id_throttle.attempts
                    id_backoff = self.calculate_backoff_seconds(id_attempts, self.identifier_policy)
                    if id_backoff > 0:
                        result["throttled"] = True
                        result["retry_after_seconds"] = int(math.ceil(id_backoff))
                        return result
        
        return result
    
    def record_attempt(self, session: Session, ip_address: str, identifier: str = None, is_admin: bool = False) -> None:
        """Record a login attempt.
        
        Updates throttle counters for IP and identifier, managing sliding window.
        
        Args:
            session: SQLAlchemy session
            ip_address: Client IP address
            identifier: Username/identifier (None for admin check per-IP only)
            is_admin: True if admin account (skip per-identifier check)
        """
        now = datetime.now(timezone.utc)
        window_expiry = now + timedelta(minutes=self.ip_policy.window_minutes)
        
        # Update IP throttle
        ip_key = f"ip:{ip_address}"
        ip_throttle = session.query(LoginThrottle).filter_by(key=ip_key).first()
        
        if not ip_throttle:
            ip_throttle = LoginThrottle(
                key=ip_key,
                attempts=1,
                last_attempt_at=now,
                expires_at=window_expiry,
            )
            session.add(ip_throttle)
        else:
            # Ensure expires_at is timezone-aware for comparison
            expires_at = ip_throttle.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at > now:
                # Window still active: increment counter
                ip_throttle.attempts += 1
                ip_throttle.last_attempt_at = now
            else:
                # Window expired: reset counter
                ip_throttle.attempts = 1
                ip_throttle.last_attempt_at = now
                ip_throttle.expires_at = window_expiry
        
        # Update per-identifier throttle (skip for admin)
        if not is_admin and identifier:
            identifier_key = f"id:local:{identifier.lower().strip()}"
            id_throttle = session.query(LoginThrottle).filter_by(key=identifier_key).first()
            
            id_window_expiry = now + timedelta(minutes=self.identifier_policy.window_minutes)
            
            if not id_throttle:
                id_throttle = LoginThrottle(
                    key=identifier_key,
                    attempts=1,
                    last_attempt_at=now,
                    expires_at=id_window_expiry,
                )
                session.add(id_throttle)
            else:
                # Ensure expires_at is timezone-aware for comparison
                expires_at = id_throttle.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                
                if expires_at > now:
                    # Window still active: increment counter
                    id_throttle.attempts += 1
                    id_throttle.last_attempt_at = now
                else:
                    # Window expired: reset counter
                    id_throttle.attempts = 1
                    id_throttle.last_attempt_at = now
                    id_throttle.expires_at = id_window_expiry
