/**
 * Setup page for LitFoundry (Task 2.5).
 * Allows initial admin account creation during setup.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'SetupPage',
  setup() {
    const bootstrapToken = ref('');
    const displayName = ref('');
    const password = ref('');
    const confirmPassword = ref('');
    const loading = ref(false);
    const setupComplete = ref(false);
    const error = ref('');
    const setupStatus = ref(null);

    const checkSetupStatus = async () => {
      try {
        const response = await fetch('/api/v1/setup/status');
        if (response.ok) {
          setupStatus.value = await response.json();
          if (setupStatus.value.complete) {
            setupComplete.value = true;
          }
        }
      } catch (err) {
        console.error('Failed to check setup status', err);
      }
    };

    const submitSetup = async (e) => {
      e.preventDefault();
      error.value = '';

      if (!bootstrapToken.value || !displayName.value || !password.value) {
        error.value = 'All fields are required';
        return;
      }

      if (password.value !== confirmPassword.value) {
        error.value = 'Passwords do not match';
        return;
      }

      if (password.value.length < 8) {
        error.value = 'Password must be at least 8 characters';
        return;
      }

      loading.value = true;
      try {
        const response = await fetch('/api/v1/setup/admin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bootstrap_token: bootstrapToken.value,
            display_name: displayName.value,
            password: password.value,
          }),
        });

        if (response.ok) {
          setupComplete.value = true;
          // Redirect to login or main app after a delay
          setTimeout(() => {
            window.location.href = '/';
          }, 2000);
        } else {
          const data = await response.json();
          error.value = data.error || 'Setup failed';
        }
      } catch (err) {
        error.value = 'Network error: ' + err.message;
      } finally {
        loading.value = false;
      }
    };

    checkSetupStatus();

    if (setupComplete.value) {
      return () =>
        h('div', { class: 'min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4' }, [
          h('div', { class: 'bg-white rounded-lg shadow-xl p-8 max-w-md w-full text-center' }, [
            h('h1', { class: 'text-2xl font-bold text-gray-900 mb-4' }, 'Setup Complete'),
            h('p', { class: 'text-gray-600 mb-4' }, 'Your LitFoundry instance has been configured.'),
            h('p', { class: 'text-sm text-gray-500' }, 'Redirecting to login...'),
          ]),
        ]);
    }

    return () =>
      h('div', { class: 'min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4' }, [
        h('div', { class: 'bg-white rounded-lg shadow-xl p-8 max-w-md w-full' }, [
          h('h1', { class: 'text-3xl font-bold text-gray-900 mb-2 text-center' }, 'LitFoundry'),
          h('p', { class: 'text-center text-gray-600 mb-6' }, 'Initial Setup'),

          error.value &&
            h('div', { class: 'bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700 text-sm' }, error.value),

          h('form', { onSubmit: submitSetup }, [
            h('div', { class: 'mb-4' }, [
              h('label', { class: 'block text-sm font-medium text-gray-700 mb-1' }, 'Bootstrap Token'),
              h('input', {
                type: 'password',
                value: bootstrapToken.value,
                onInput: (e) => { bootstrapToken.value = e.target.value; },
                placeholder: 'Enter your bootstrap token',
                disabled: loading.value,
                class: 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
              }),
            ]),

            h('div', { class: 'mb-4' }, [
              h('label', { class: 'block text-sm font-medium text-gray-700 mb-1' }, 'Display Name'),
              h('input', {
                type: 'text',
                value: displayName.value,
                onInput: (e) => { displayName.value = e.target.value; },
                placeholder: 'Administrator',
                disabled: loading.value,
                class: 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
              }),
            ]),

            h('div', { class: 'mb-4' }, [
              h('label', { class: 'block text-sm font-medium text-gray-700 mb-1' }, 'Password'),
              h('input', {
                type: 'password',
                value: password.value,
                onInput: (e) => { password.value = e.target.value; },
                placeholder: 'Secure password',
                disabled: loading.value,
                class: 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
              }),
            ]),

            h('div', { class: 'mb-6' }, [
              h('label', { class: 'block text-sm font-medium text-gray-700 mb-1' }, 'Confirm Password'),
              h('input', {
                type: 'password',
                value: confirmPassword.value,
                onInput: (e) => { confirmPassword.value = e.target.value; },
                placeholder: 'Confirm password',
                disabled: loading.value,
                class: 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
              }),
            ]),

            h('button', {
              type: 'submit',
              disabled: loading.value,
              class: 'w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition disabled:opacity-50 disabled:cursor-not-allowed',
            }, loading.value ? 'Setting up...' : 'Create Admin Account'),
          ]),
        ]),
      ]);
  },
};
