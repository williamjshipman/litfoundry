/**
 * Password change page for LitFoundry (Task 4.5).
 * Shows when user must change password after forced-change flag is set.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'PasswordChangePage',
  setup() {
    const currentPassword = ref('');
    const newPassword = ref('');
    const confirmPassword = ref('');
    const error = ref('');
    const loading = ref(false);

    const handleSubmit = async (e) => {
      e.preventDefault();
      error.value = '';

      if (newPassword.value !== confirmPassword.value) {
        error.value = 'Passwords do not match';
        return;
      }

      if (newPassword.value.length < 8) {
        error.value = 'Password must be at least 8 characters';
        return;
      }

      loading.value = true;

      try {
        const response = await fetch('/api/v1/auth/password', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            current_password: currentPassword.value,
            new_password: newPassword.value,
          }),
        });

        if (response.ok) {
          window.location.href = '/dashboard';
        } else {
          const data = await response.json();
          error.value = data.message || 'Password change failed';
        }
      } catch (err) {
        error.value = 'An error occurred';
      } finally {
        loading.value = false;
      }
    };

    return () =>
      h('div', { class: 'min-h-screen bg-yellow-50 flex justify-center py-12 px-4' }, [
        h('div', { class: 'max-w-md w-full' }, [
          h('div', { class: 'text-center mb-6' }, [
            h('h1', { class: 'text-2xl font-bold text-orange-600' }, 'Change Your Password'),
            h('p', { class: 'text-gray-600 mt-2' }, 'Your password must be changed before continuing'),
          ]),
          h('div', { class: 'bg-white p-8 rounded-lg shadow' }, [
            error.value && h('div', { class: 'text-red-600 mb-4' }, error.value),
            h('form', { onSubmit: handleSubmit, class: 'space-y-4' }, [
              h('div', {}, [
                h('label', { class: 'block text-sm font-medium mb-1' }, 'Current Password'),
                h('input', {
                  type: 'password',
                  required: true,
                  value: currentPassword.value,
                  onInput: (e) => (currentPassword.value = e.target.value),
                  class: 'w-full px-3 py-2 border rounded-md',
                }),
              ]),
              h('div', {}, [
                h('label', { class: 'block text-sm font-medium mb-1' }, 'New Password'),
                h('input', {
                  type: 'password',
                  required: true,
                  value: newPassword.value,
                  onInput: (e) => (newPassword.value = e.target.value),
                  class: 'w-full px-3 py-2 border rounded-md',
                }),
              ]),
              h('div', {}, [
                h('label', { class: 'block text-sm font-medium mb-1' }, 'Confirm Password'),
                h('input', {
                  type: 'password',
                  required: true,
                  value: confirmPassword.value,
                  onInput: (e) => (confirmPassword.value = e.target.value),
                  class: 'w-full px-3 py-2 border rounded-md',
                }),
              ]),
              h('button', {
                type: 'submit',
                disabled: loading.value,
                class: 'w-full py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700',
              }, loading.value ? 'Changing...' : 'Change Password'),
            ]),
          ]),
        ]),
      ]);
  },
};
