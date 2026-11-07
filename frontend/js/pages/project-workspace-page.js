/**
 * Project workspace page with tabs for different sections.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

/**
 * Sharing Tab Component
 */
function SharingTab({ projectId, apiClient }) {
  const visibility = ref('none');
  const acl = ref([]);
  const effectivePerms = ref([]);
  const userSearchTerm = ref('');
  const userSearchResults = ref([]);
  const showPublicEditWarning = ref(false);
  const selectedNewRole = ref('viewer');
  const selectedNewUserId = ref('');

  const loadSharing = async () => {
    try {
      const response = await apiClient.get(`/api/v1/projects/${projectId}/sharing`);
      visibility.value = response.visibility;
      acl.value = response.acl || [];
      effectivePerms.value = response.effective_permissions || [];
    } catch (error) {
      console.error('Failed to load sharing:', error);
    }
  };

  const updateVisibility = async (newVisibility) => {
    try {
      if (newVisibility === 'editor' && visibility.value !== 'editor') {
        showPublicEditWarning.value = true;
        selectedNewRole.value = newVisibility;
        return;
      }
      
      await apiClient.put(`/api/v1/projects/${projectId}/sharing`, {
        visibility: newVisibility,
        public_edit_confirmation: newVisibility === 'editor',
      });
      visibility.value = newVisibility;
      showPublicEditWarning.value = false;
      await loadSharing();
    } catch (error) {
      console.error('Failed to update visibility:', error);
    }
  };

  const searchUsers = async () => {
    if (!userSearchTerm.value || userSearchTerm.value.length < 2) {
      userSearchResults.value = [];
      return;
    }

    try {
      const response = await apiClient.get('/api/v1/users/lookup', {
        q: userSearchTerm.value,
        limit: 10,
      });
      userSearchResults.value = response.items || [];
    } catch (error) {
      console.error('Failed to search users:', error);
      userSearchResults.value = [];
    }
  };

  const addACLEntry = async (userId, role) => {
    try {
      const newAcl = acl.value.map(e => ({
        user_id: e.user_id,
        role: e.role,
      }));
      
      // Add or update entry
      const existingIndex = newAcl.findIndex(e => e.user_id === userId);
      if (existingIndex >= 0) {
        newAcl[existingIndex].role = role;
      } else {
        newAcl.push({ user_id: userId, role });
      }

      await apiClient.put(`/api/v1/projects/${projectId}/sharing`, {
        acl: newAcl,
      });
      
      userSearchTerm.value = '';
      userSearchResults.value = [];
      await loadSharing();
    } catch (error) {
      console.error('Failed to add ACL entry:', error);
    }
  };

  const removeACLEntry = async (userId) => {
    try {
      const newAcl = acl.value
        .filter(e => e.user_id !== userId)
        .map(e => ({
          user_id: e.user_id,
          role: e.role,
        }));

      await apiClient.put(`/api/v1/projects/${projectId}/sharing`, {
        acl: newAcl,
      });
      
      await loadSharing();
    } catch (error) {
      console.error('Failed to remove ACL entry:', error);
    }
  };

  // Initial load
  loadSharing();

  return h('div', { class: 'sharing-tab' }, [
    // Visibility Selector
    h('section', { class: 'card' }, [
      h('h2', 'Visibility'),
      h('p', { class: 'text-muted' }, 'Control who can discover this project'),
      h('div', { class: 'visibility-options' }, [
        h('label', [
          h('input', {
            type: 'radio',
            name: 'visibility',
            value: 'none',
            checked: visibility.value === 'none',
            onChange: () => updateVisibility('none'),
          }),
          ' Private (owner only)',
        ]),
        h('label', [
          h('input', {
            type: 'radio',
            name: 'visibility',
            value: 'viewer',
            checked: visibility.value === 'viewer',
            onChange: () => updateVisibility('viewer'),
          }),
          ' Public view (anyone can read)',
        ]),
        h('label', [
          h('input', {
            type: 'radio',
            name: 'visibility',
            value: 'editor',
            checked: visibility.value === 'editor',
            onChange: () => updateVisibility('editor'),
          }),
          ' Public edit (anyone can edit)',
        ]),
      ]),
    ]),

    // Public Edit Warning
    showPublicEditWarning.value && h('div', { class: 'warning-dialog' }, [
      h('h3', 'Make Project Public for Editing?'),
      h('p', 'Anyone with access to this installation will be able to modify this project.'),
      h('div', { class: 'dialog-actions' }, [
        h('button', {
          onClick: () => {
            showPublicEditWarning.value = false;
            selectedNewRole.value = '';
          },
        }, 'Cancel'),
        h('button', {
          class: 'btn-primary',
          onClick: () => updateVisibility('editor'),
        }, 'Confirm'),
      ]),
    ]),

    // ACL Management
    h('section', { class: 'card' }, [
      h('h2', 'Per-User Access'),
      h('p', { class: 'text-muted' }, 'Grant or deny access for specific users'),
      
      // User Search
      h('div', { class: 'search-box' }, [
        h('input', {
          type: 'text',
          placeholder: 'Search for user...',
          value: userSearchTerm.value,
          onInput: (e) => {
            userSearchTerm.value = e.target.value;
            searchUsers();
          },
        }),
        userSearchResults.value.length > 0 && h('ul', { class: 'search-results' }, [
          ...userSearchResults.value.map(user =>
            h('li', { key: user.id }, [
              h('div', { class: 'user-item' }, [
                h('span', user.username),
                h('select', {
                  value: 'viewer',
                  onChange: (e) => addACLEntry(user.id, e.target.value),
                }, [
                  h('option', { value: 'viewer' }, 'Viewer'),
                  h('option', { value: 'editor' }, 'Editor'),
                  h('option', { value: 'deny' }, 'Deny'),
                ]),
              ]),
            ])
          ),
        ]),
      ]),

      // Current ACL
      acl.value.length > 0 && h('div', { class: 'acl-list' }, [
        h('h3', 'Current Access'),
        h('ul', [
          ...acl.value.map(entry =>
            h('li', { key: entry.user_id }, [
              h('div', { class: 'acl-item' }, [
                h('span', entry.user_id),
                h('span', { class: 'role-badge' }, entry.role),
                h('button', {
                  onClick: () => removeACLEntry(entry.user_id),
                }, '✕'),
              ]),
            ])
          ),
        ]),
      ]),
    ]),

    // Effective Permissions
    h('section', { class: 'card' }, [
      h('h2', 'Effective Permissions Preview'),
      h('p', { class: 'text-muted' }, 'How the access rules resolve for each user'),
      h('table', { class: 'permissions-table' }, [
        h('thead', [
          h('tr', [
            h('th', 'User'),
            h('th', 'Access Level'),
            h('th', 'Rule'),
          ]),
        ]),
        h('tbody', [
          ...effectivePerms.value.map(perm =>
            h('tr', { key: perm.user_id }, [
              h('td', perm.username),
              h('td', perm.access_level),
              h('td', { class: 'text-muted' }, perm.rule),
            ])
          ),
        ]),
      ]),
    ]),
  ]);
}

/**
 * Project workspace page
 */
export function ProjectWorkspacePage(props) {
  const { projectId, apiClient } = props;
  const currentTab = ref('overview');

  return h('div', { class: 'project-workspace' }, [
    // Tab Navigation
    h('nav', { class: 'tabs' }, [
      h('button', {
        class: currentTab.value === 'overview' ? 'tab-active' : '',
        onClick: () => currentTab.value = 'overview',
      }, 'Overview'),
      h('button', {
        class: currentTab.value === 'sharing' ? 'tab-active' : '',
        onClick: () => currentTab.value = 'sharing',
      }, 'Sharing'),
      h('button', {
        class: currentTab.value === 'history' ? 'tab-active' : '',
        onClick: () => currentTab.value = 'history',
      }, 'History'),
    ]),

    // Tab Content
    h('div', { class: 'tab-content' }, [
      currentTab.value === 'overview' && h('div', 'Project Overview Tab'),
      currentTab.value === 'sharing' && SharingTab({ projectId, apiClient }),
      currentTab.value === 'history' && h('div', 'Project History Tab'),
    ]),
  ]);
}

export default ProjectWorkspacePage;
