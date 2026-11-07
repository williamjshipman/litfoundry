/**
 * Sign-in page for LitFoundry.
 * Handles both local and Active Directory authentication.
 * Uses HTTP-only cookies (no tokens in web storage).
 */

import { h, ref, onMounted } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'SignInPage',
  setup() {
    const username = ref('');
    const password = ref('');
    const error = ref('');
    const loading = ref(false);
    const selectedProvider = ref('local');
    const availableMethods = ref([]);
    const methodsLoading = ref(true);

    const fetchAvailableMethods = async () => {
      try {
        const response = await fetch('/api/v1/auth/methods', {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          availableMethods.value = data.methods || ['local'];
          // If AD is available, select it as default; otherwise use local
          if (availableMethods.value.includes('active_directory')) {
            selectedProvider.value = 'active_directory';
          }
        } else {
          availableMethods.value = ['local'];
        }
      } catch (err) {
        availableMethods.value = ['local'];
      } finally {
        methodsLoading.value = false;
      }
    };

    const handleSubmit = async (e) => {
      e.preventDefault();
      error.value = '';
      loading.value = true;

      try {
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            username: username.value,
            password: password.value,
            provider: selectedProvider.value,
          }),
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

    onMounted(() => {
      fetchAvailableMethods();
    });

    const showMethodSelector = availableMethods.value.length > 1;

    return () =>
      h('div', { class: 'min-h-screen bg-gray-50 flex justify-center py-12 px-4' }, [
        h('div', { class: 'max-w-md w-full' }, [
          h('div', { class: 'text-center mb-6' }, [
            h('h1', { class: 'text-3xl font-bold' }, 'LitFoundry'),
            h('p', { class: 'text-gray-600' }, 'Sign in'),
          ]),
          h('div', { class: 'bg-white p-8 rounded-lg shadow' }, [
            error.value && h('div', { class: 'text-red-600 mb-4 p-2 bg-red-50 rounded' }, error.value),
            
            // Method selector (shown if AD is available)
            showMethodSelector && h('div', { class: 'mb-6 border-b pb-4' }, [
              h('label', { class: 'block text-sm font-medium mb-2' }, 'Sign in with'),
              h('div', { class: 'space-y-2' }, [
                h('label', { class: 'flex items-center' }, [
                  h('input', {
                    type: 'radio',
                    value: 'local',
                    checked: selectedProvider.value === 'local',
                    onChange: () => (selectedProvider.value = 'local'),
                    class: 'mr-2',
                  }),
                  h('span', 'LitFoundry account'),
                ]),
                availableMethods.value.includes('active_directory') && h('label', { class: 'flex items-center' }, [
                  h('input', {
                    type: 'radio',
                    value: 'active_directory',
                    checked: selectedProvider.value === 'active_directory',
                    onChange: () => (selectedProvider.value = 'active_directory'),
                    class: 'mr-2',
                  }),
                  h('span', 'Active Directory'),
                ]),
              ]),
            ]),

            h('form', { onSubmit: handleSubmit, class: 'space-y-4' }, [
              h('div', {}, [
                h('label', { class: 'block text-sm font-medium mb-1' },
                  selectedProvider.value === 'active_directory' ? 'Domain Username' : 'Username'
                ),
                h('input', {
                  type: 'text',
                  required: true,
                  value: username.value,
                  onInput: (e) => (username.value = e.target.value),
                  placeholder: selectedProvider.value === 'active_directory' ? 'DOMAIN\\username or user@domain.com' : 'username',
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
                disabled: loading.value || methodsLoading.value,
                class: 'w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400',
              }, loading.value ? 'Signing in...' : 'Sign in'),
            ]),
          ]),
        ]),
      ]);
  },
};
