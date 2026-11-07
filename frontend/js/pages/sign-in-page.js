/**
 * Sign-in page for LitFoundry (Task 4.5).
 * Handles local username/password authentication.
 * Uses HTTP-only cookies (no tokens in web storage).
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'SignInPage',
  setup() {
    const username = ref('');
    const password = ref('');
    const error = ref('');
    const loading = ref(false);

    const handleSubmit = async (e) => {
      e.preventDefault();
      error.value = '';
      loading.value = true;

      try {
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ username: username.value, password: password.value }),
        });

        if (response.ok) {
          window.location.href = '/dashboard';
        } else {
          const data = await response.json();
          error.value = data.message || 'Sign-in failed';
        }
      } catch (err) {
        error.value = 'An error occurred';
      } finally {
        loading.value = false;
      }
    };

    return () =>
      h('div', { class: 'min-h-screen bg-gray-50 flex justify-center py-12 px-4' }, [
        h('div', { class: 'max-w-md w-full' }, [
          h('div', { class: 'text-center mb-6' }, [
            h('h1', { class: 'text-3xl font-bold' }, 'LitFoundry'),
            h('p', { class: 'text-gray-600' }, 'Sign in'),
          ]),
          h('div', { class: 'bg-white p-8 rounded-lg shadow' }, [
            error.value && h('div', { class: 'text-red-600 mb-4' }, error.value),
            h('form', { onSubmit: handleSubmit, class: 'space-y-4' }, [
              h('div', {}, [
                h('label', { class: 'block text-sm font-medium mb-1' }, 'Username'),
                h('input', {
                  type: 'text',
                  required: true,
                  value: username.value,
                  onInput: (e) => (username.value = e.target.value),
                  class: 'w-full px-3 py-2 border rounded-md',
                }),
              ]),
              h('div', {}, [
                h('label', { class: 'block text-sm font-medium mb-1' }, 'Password'),
                h('input', {
                  type: 'password',
                  required: true,
                  value: password.value,
                  onInput: (e) => (password.value = e.target.value),
                  class: 'w-full px-3 py-2 border rounded-md',
                }),
              ]),
              h('button', {
                type: 'submit',
                disabled: loading.value,
                class: 'w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700',
              }, loading.value ? 'Signing in...' : 'Sign in'),
            ]),
          ]),
        ]),
      ]);
  },
};
