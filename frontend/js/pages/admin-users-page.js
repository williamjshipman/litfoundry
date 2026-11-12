/**
 * Admin Users page for LitFoundry (Task 5.2).
 * Allows admin to list, create (local and AD), enable/disable, reset password, and revoke sessions for users.
 */

import { h, ref, reactive } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AdminUsersPage',
  setup() {
    const users = ref([]);
    const loading = ref(false);
    const error = ref('');
    const showCreateForm = ref(false);
    const createMode = ref('local'); // 'local' or 'active_directory'
    const newUser = reactive({ username: '', password: '', role: 'user', account_type: 'local' });
    const adUser = reactive({
      samaccountname: '',
      upn: '',
      sid: '',
      role: 'user',
      account_type: 'active_directory',
    });
    const selectedUser = ref(null);
    const showResetConfirm = ref(false);
    const showRevokeConfirm = ref(false);
    const resolveError = ref('');

    const loadUsers = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/admin/users', {
          credentials: 'include',
        });
        if (response.ok) {
          users.value = await response.json();
        }
      } catch (err) {
        error.value = 'Failed to load users';
      } finally {
        loading.value = false;
      }
    };

    const createUser = async () => {
      try {
        if (createMode.value === 'local') {
          const response = await fetch('/api/v1/admin/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username: newUser.username, password: newUser.password, role: newUser.role, account_type: 'local' }),
          });
          if (response.ok) {
            newUser.username = '';
            newUser.password = '';
            newUser.role = 'user';
            showCreateForm.value = false;
            createMode.value = 'local';
            await loadUsers();
          } else {
            const data = await response.json();
            error.value = data.message || 'Failed to create user';
          }
        } else {
          // AD user creation
          const response = await fetch('/api/v1/admin/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
              samaccountname: adUser.samaccountname,
              upn: adUser.upn,
              sid: adUser.sid,
              role: adUser.role,
              account_type: 'active_directory',
            }),
          });
          if (response.ok) {
            adUser.samaccountname = '';
            adUser.upn = '';
            adUser.sid = '';
            adUser.role = 'user';
            showCreateForm.value = false;
            createMode.value = 'local';
            await loadUsers();
          } else {
            const data = await response.json();
            error.value = data.message || 'Failed to create AD user';
          }
        }
      } catch (err) {
        error.value = 'Failed to create user';
      }
    };

    const toggleUserActive = async (user) => {
      try {
        const response = await fetch(`/api/v1/admin/users/${user.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ active: !user.active }),
        });
        if (response.ok) {
          await loadUsers();
        }
      } catch (err) {
        error.value = 'Failed to update user';
      }
    };

    const resetPassword = async () => {
      if (!selectedUser.value) return;
      try {
        const password = prompt('Enter new password:');
        if (!password) return;
        const response = await fetch(`/api/v1/admin/users/${selectedUser.value.id}/reset-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ password }),
        });
        if (response.ok) {
          showResetConfirm.value = false;
          await loadUsers();
        }
      } catch (err) {
        error.value = 'Failed to reset password';
      }
    };

    const revokeSessions = async () => {
      if (!selectedUser.value) return;
      try {
        const response = await fetch(`/api/v1/admin/users/${selectedUser.value.id}/revoke-sessions`, {
          method: 'POST',
          credentials: 'include',
        });
        if (response.ok) {
          showRevokeConfirm.value = false;
          await loadUsers();
        }
      } catch (err) {
        error.value = 'Failed to revoke sessions';
      }
    };

    const resolveAdUser = async () => {
      resolveError.value = '';
      if (!adUser.samaccountname && !adUser.upn) {
        resolveError.value = 'Enter sAMAccountName or UPN';
        return;
      }

      try {
        const response = await fetch('/api/v1/admin/ad-directory/resolve-user', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            samaccountname: adUser.samaccountname,
            upn: adUser.upn,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          adUser.samaccountname = data.samaccountname || '';
          adUser.upn = data.upn || '';
          adUser.sid = data.sid || '';
        } else {
          const data = await response.json();
          resolveError.value = data.message || 'Failed to resolve user';
        }
      } catch (err) {
        resolveError.value = 'An error occurred';
      }
    };

    loadUsers();

    return () =>
      h('div', { class: 'p-6 max-w-4xl mx-auto' }, [
        h('h1', { class: 'text-3xl font-bold mb-6' }, 'User Management'),

        error.value && h('div', { class: 'text-red-600 mb-4 p-3 bg-red-50 rounded' }, error.value),

        h('button', {
          onClick: () => (showCreateForm.value = !showCreateForm.value),
          class: 'mb-6 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700',
        }, 'Create User'),

        showCreateForm.value &&
          h('div', { class: 'bg-gray-100 p-6 rounded-lg mb-6' }, [
            h('h2', { class: 'font-bold mb-4 text-lg' }, 'New User'),

            // Account type selector
            h('div', { class: 'mb-4' }, [
              h('label', { class: 'block font-medium mb-2' }, 'Account Type'),
              h('div', { class: 'flex gap-4' }, [
                h('label', { class: 'flex items-center' }, [
                  h('input', {
                    type: 'radio',
                    value: 'local',
                    checked: createMode.value === 'local',
                    onChange: () => (createMode.value = 'local'),
                    class: 'mr-2',
                  }),
                  h('span', 'Local Account'),
                ]),
                h('label', { class: 'flex items-center' }, [
                  h('input', {
                    type: 'radio',
                    value: 'active_directory',
                    checked: createMode.value === 'active_directory',
                    onChange: () => (createMode.value = 'active_directory'),
                    class: 'mr-2',
                  }),
                  h('span', 'Active Directory'),
                ]),
              ]),
            ]),

            // Local user form
            createMode.value === 'local' && h('div', { class: 'space-y-3' }, [
              h('input', {
                type: 'text',
                placeholder: 'Username',
                value: newUser.username,
                onInput: (e) => (newUser.username = e.target.value),
                class: 'w-full px-3 py-2 border rounded',
              }),
              h('input', {
                type: 'password',
                placeholder: 'Password',
                value: newUser.password,
                onInput: (e) => (newUser.password = e.target.value),
                class: 'w-full px-3 py-2 border rounded',
              }),
              h('select', {
                value: newUser.role,
                onChange: (e) => (newUser.role = e.target.value),
                class: 'w-full px-3 py-2 border rounded',
              }, [
                h('option', { value: 'user' }, 'User'),
                h('option', { value: 'admin' }, 'Admin'),
              ]),
              h('div', { class: 'flex gap-2' }, [
                h('button', {
                  onClick: createUser,
                  class: 'px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700',
                }, 'Create'),
                h('button', {
                  onClick: () => (showCreateForm.value = false),
                  class: 'px-4 py-2 bg-gray-500 text-white rounded',
                }, 'Cancel'),
              ]),
            ]),

            // AD user form
            createMode.value === 'active_directory' && h('div', { class: 'space-y-4' }, [
              h('div', { class: 'p-3 bg-blue-50 rounded border border-blue-200' }, [
                h('p', { class: 'text-sm text-blue-900 mb-2' }, 'Lookup Active Directory user first:'),
                h('div', { class: 'space-y-2' }, [
                  h('input', {
                    type: 'text',
                    placeholder: 'sAMAccountName (e.g., jsmith)',
                    value: adUser.samaccountname,
                    onInput: (e) => (adUser.samaccountname = e.target.value),
                    class: 'w-full px-3 py-2 border rounded',
                  }),
                  h('input', {
                    type: 'text',
                    placeholder: 'UPN (e.g., jsmith@domain.com)',
                    value: adUser.upn,
                    onInput: (e) => (adUser.upn = e.target.value),
                    class: 'w-full px-3 py-2 border rounded',
                  }),
                  resolveError.value && h('p', { class: 'text-red-600 text-sm' }, resolveError.value),
                  h('button', {
                    onClick: resolveAdUser,
                    class: 'px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700',
                  }, 'Resolve User in AD'),
                ]),
              ]),

              // Display resolved info
              adUser.sid && h('div', { class: 'p-3 bg-green-50 rounded border border-green-200' }, [
                h('p', { class: 'text-sm font-semibold mb-2' }, 'Resolved User:'),
                h('dl', { class: 'text-sm space-y-1' }, [
                  [h('dt', { class: 'font-semibold' }, 'sAMAccountName:'), h('dd', adUser.samaccountname)],
                  [h('dt', { class: 'font-semibold' }, 'UPN:'), h('dd', adUser.upn)],
                  [h('dt', { class: 'font-semibold' }, 'SID:'), h('dd', { class: 'break-all text-xs' }, adUser.sid)],
                ]),
              ]),

              h('select', {
                value: adUser.role,
                onChange: (e) => (adUser.role = e.target.value),
                class: 'w-full px-3 py-2 border rounded',
              }, [
                h('option', { value: 'user' }, 'User'),
                h('option', { value: 'admin' }, 'Admin'),
              ]),

              h('div', { class: 'flex gap-2' }, [
                h('button', {
                  onClick: createUser,
                  disabled: !adUser.sid,
                  class: 'px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400',
                }, 'Create AD User'),
                h('button', {
                  onClick: () => (showCreateForm.value = false),
                  class: 'px-4 py-2 bg-gray-500 text-white rounded',
                }, 'Cancel'),
              ]),
            ]),
          ]),

        h('div', { class: 'overflow-x-auto' }, [
          h('table', { class: 'w-full border' }, [
            h('thead', {}, [
              h('tr', { class: 'bg-gray-200' }, [
                h('th', { class: 'px-4 py-2 text-left' }, 'Username'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Type'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Role'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Status'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Actions'),
              ]),
            ]),
            h('tbody', {}, users.value.map((user) =>
              h('tr', { key: user.id, class: 'border-b' }, [
                h('td', { class: 'px-4 py-2' }, user.username),
                h('td', { class: 'px-4 py-2 text-sm' }, user.account_type === 'active_directory' ? 'AD' : 'Local'),
                h('td', { class: 'px-4 py-2' }, user.role),
                h('td', { class: 'px-4 py-2' }, user.active ? 'Active' : 'Inactive'),
                h('td', { class: 'px-4 py-2 space-x-2' }, [
                  h('button', {
                    onClick: () => toggleUserActive(user),
                    class: 'px-2 py-1 bg-gray-500 text-white text-sm rounded hover:bg-gray-600',
                  }, user.active ? 'Disable' : 'Enable'),
                  user.account_type === 'local' && h('button', {
                    onClick: () => { selectedUser.value = user; showResetConfirm.value = true; },
                    class: 'px-2 py-1 bg-orange-500 text-white text-sm rounded hover:bg-orange-600',
                  }, 'Reset'),
                  h('button', {
                    onClick: () => { selectedUser.value = user; showRevokeConfirm.value = true; },
                    class: 'px-2 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700',
                  }, 'Revoke'),
                ]),
              ]),
            )),
          ]),
        ]),

        showResetConfirm.value &&
          h('div', { class: 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center' }, [
            h('div', { class: 'bg-white p-6 rounded-lg' }, [
              h('p', { class: 'mb-4' }, `Reset password for ${selectedUser.value?.username}?`),
              h('div', { class: 'flex gap-2' }, [
                h('button', {
                  onClick: resetPassword,
                  class: 'px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700',
                }, 'Confirm'),
                h('button', {
                  onClick: () => (showResetConfirm.value = false),
                  class: 'px-4 py-2 bg-gray-300 rounded hover:bg-gray-400',
                }, 'Cancel'),
              ]),
            ]),
          ]),

        showRevokeConfirm.value &&
          h('div', { class: 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center' }, [
            h('div', { class: 'bg-white p-6 rounded-lg' }, [
              h('p', { class: 'mb-4' }, `Revoke all sessions for ${selectedUser.value?.username}?`),
              h('div', { class: 'flex gap-2' }, [
                h('button', {
                  onClick: revokeSessions,
                  class: 'px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700',
                }, 'Confirm'),
                h('button', {
                  onClick: () => (showRevokeConfirm.value = false),
                  class: 'px-4 py-2 bg-gray-300 rounded hover:bg-gray-400',
                }, 'Cancel'),
              ]),
            ]),
          ]),
      ]);
  },
};
