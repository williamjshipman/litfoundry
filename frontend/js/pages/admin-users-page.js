/**
 * Admin Users page for LitFoundry (Task 5.2).
 * Allows admin to list, create, enable/disable, reset password, and revoke sessions for users.
 */

import { h, ref, reactive } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AdminUsersPage',
  setup() {
    const users = ref([]);
    const loading = ref(false);
    const error = ref('');
    const showCreateForm = ref(false);
    const newUser = reactive({ username: '', password: '', role: 'user' });
    const selectedUser = ref(null);
    const showResetConfirm = ref(false);
    const showRevokeConfirm = ref(false);

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
        const response = await fetch('/api/v1/admin/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(newUser),
        });
        if (response.ok) {
          newUser.username = '';
          newUser.password = '';
          newUser.role = 'user';
          showCreateForm.value = false;
          await loadUsers();
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

    loadUsers();

    return () =>
      h('div', { class: 'p-6 max-w-4xl mx-auto' }, [
        h('h1', { class: 'text-3xl font-bold mb-6' }, 'User Management'),

        error.value && h('div', { class: 'text-red-600 mb-4' }, error.value),

        h('button', {
          onClick: () => (showCreateForm.value = !showCreateForm.value),
          class: 'mb-6 px-4 py-2 bg-blue-600 text-white rounded-md',
        }, 'Create User'),

        showCreateForm.value &&
          h('div', { class: 'bg-gray-100 p-4 rounded-md mb-6' }, [
            h('h2', { class: 'font-bold mb-4' }, 'New User'),
            h('div', { class: 'space-y-3' }, [
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
              h('button', {
                onClick: createUser,
                class: 'px-4 py-2 bg-green-600 text-white rounded',
              }, 'Create'),
            ]),
          ]),

        h('div', { class: 'overflow-x-auto' }, [
          h('table', { class: 'w-full border' }, [
            h('thead', {}, [
              h('tr', { class: 'bg-gray-200' }, [
                h('th', { class: 'px-4 py-2 text-left' }, 'Username'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Role'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Status'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Actions'),
              ]),
            ]),
            h('tbody', {}, users.value.map((user) =>
              h('tr', { key: user.id, class: 'border-b' }, [
                h('td', { class: 'px-4 py-2' }, user.username),
                h('td', { class: 'px-4 py-2' }, user.role),
                h('td', { class: 'px-4 py-2' }, user.active ? 'Active' : 'Inactive'),
                h('td', { class: 'px-4 py-2 space-x-2' }, [
                  h('button', {
                    onClick: () => toggleUserActive(user),
                    class: 'px-2 py-1 bg-gray-500 text-white text-sm rounded',
                  }, user.active ? 'Disable' : 'Enable'),
                  h('button', {
                    onClick: () => { selectedUser.value = user; showResetConfirm.value = true; },
                    class: 'px-2 py-1 bg-orange-500 text-white text-sm rounded',
                  }, 'Reset'),
                  h('button', {
                    onClick: () => { selectedUser.value = user; showRevokeConfirm.value = true; },
                    class: 'px-2 py-1 bg-red-600 text-white text-sm rounded',
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
                  class: 'px-4 py-2 bg-orange-600 text-white rounded',
                }, 'Confirm'),
                h('button', {
                  onClick: () => (showResetConfirm.value = false),
                  class: 'px-4 py-2 bg-gray-300 rounded',
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
                  class: 'px-4 py-2 bg-red-600 text-white rounded',
                }, 'Confirm'),
                h('button', {
                  onClick: () => (showRevokeConfirm.value = false),
                  class: 'px-4 py-2 bg-gray-300 rounded',
                }, 'Cancel'),
              ]),
            ]),
          ]),
      ]);
  },
};
