/**
 * Admin Authentication page for LitFoundry (Task 4.3).
 * Manages Active Directory configuration, testing, enable/disable.
 * Admin-only access.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AdminAuthenticationPage',
  setup() {
    const adConfig = ref(null);
    const adEnabled = ref(false);
    const loading = ref(true);
    const testResults = ref(null);
    const testLoading = ref(false);
    const testError = ref('');
    const editMode = ref(false);
    const formData = ref({});
    const formError = ref('');
    const formLoading = ref(false);

    const loadAdConfig = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/admin/ad-directory', {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          adConfig.value = data;
          adEnabled.value = data.enabled || false;
          formData.value = { ...data };
        } else if (response.status === 404) {
          // No AD configured yet
          adConfig.value = null;
          adEnabled.value = false;
          formData.value = {
            domain_name: '',
            netbios_name: '',
            upn_suffixes: [],
            domain_controllers: [],
            base_dn: '',
            tls_mode: 'ldaps',
            connection_timeout: 5,
            read_timeout: 10,
            revalidation_interval_minutes: 15,
            grace_period_minutes: 60,
            service_account_username: '',
          };
        }
      } catch (err) {
        console.error('Failed to load AD config', err);
      } finally {
        loading.value = false;
      }
    };

    const handleTestConnection = async () => {
      testLoading.value = true;
      testError.value = '';
      testResults.value = null;

      try {
        const response = await fetch('/api/v1/admin/ad-directory/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (response.ok) {
          testResults.value = await response.json();
        } else {
          const data = await response.json();
          testError.value = data.message || 'Test failed';
        }
      } catch (err) {
        testError.value = 'An error occurred during testing';
      } finally {
        testLoading.value = false;
      }
    };

    const handleSaveConfig = async () => {
      formLoading.value = true;
      formError.value = '';

      try {
        const payload = { ...formData.value };
        // Remove password if empty (client-side, server won't accept empty password)
        if (!payload.service_account_password) {
          delete payload.service_account_password;
        }

        const response = await fetch('/api/v1/admin/ad-directory', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        });

        if (response.ok) {
          adConfig.value = await response.json();
          adEnabled.value = adConfig.value.enabled || false;
          editMode.value = false;
          // Clear password field
          formData.value.service_account_password = '';
        } else {
          const data = await response.json();
          formError.value = data.message || 'Failed to save configuration';
        }
      } catch (err) {
        formError.value = 'An error occurred';
      } finally {
        formLoading.value = false;
      }
    };

    const handleToggleEnabled = async () => {
      formLoading.value = true;
      formError.value = '';

      try {
        const payload = { ...adConfig.value, enabled: !adEnabled.value };
        delete payload.service_account_password; // Never send password on toggle

        const response = await fetch('/api/v1/admin/ad-directory', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        });

        if (response.ok) {
          adConfig.value = await response.json();
          adEnabled.value = adConfig.value.enabled || false;
        } else {
          const data = await response.json();
          formError.value = data.message || 'Failed to toggle AD';
        }
      } catch (err) {
        formError.value = 'An error occurred';
      } finally {
        formLoading.value = false;
      }
    };

    const handleDeleteConfig = async () => {
      if (!confirm('Are you sure you want to remove the Active Directory configuration?')) {
        return;
      }

      formLoading.value = true;
      formError.value = '';

      try {
        const response = await fetch('/api/v1/admin/ad-directory', {
          method: 'DELETE',
          credentials: 'include',
        });

        if (response.ok) {
          adConfig.value = null;
          adEnabled.value = false;
          testResults.value = null;
          formError.value = '';
        } else {
          const data = await response.json();
          formError.value = data.message || 'Failed to delete configuration';
        }
      } catch (err) {
        formError.value = 'An error occurred';
      } finally {
        formLoading.value = false;
      }
    };

    loadAdConfig();

    return () =>
      h('div', { class: 'p-6 max-w-4xl mx-auto' }, [
        h('h1', { class: 'text-3xl font-bold mb-6' }, 'Authentication'),

        loading.value && h('p', { class: 'text-gray-600' }, 'Loading...'),

        !loading.value && h('div', { class: 'grid gap-6' }, [
          // Status section
          h('div', { class: 'bg-white p-6 rounded-lg shadow' }, [
            h('h2', { class: 'text-2xl font-bold mb-4' }, 'Active Directory Status'),
            h('div', { class: 'space-y-4' }, [
              h('div', { class: 'flex items-center justify-between' }, [
                h('span', { class: 'font-semibold' }, 'Status'),
                h('span', {
                  class: adEnabled.value
                    ? 'px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold'
                    : 'px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-semibold',
                },
                adEnabled.value ? 'Enabled' : 'Disabled'
                ),
              ]),
              adConfig.value && h('div', { class: 'text-sm text-gray-600' }, [
                h('p', `Domain: ${adConfig.value.domain_name}`),
                h('p', `Controllers: ${adConfig.value.domain_controllers?.join(', ') || 'Not configured'}`),
              ]),
            ]),
          ]),

          // Configuration section
          adConfig.value && !editMode.value && h('div', { class: 'bg-white p-6 rounded-lg shadow' }, [
            h('h2', { class: 'text-2xl font-bold mb-4' }, 'Configuration'),
            h('dl', { class: 'grid grid-cols-2 gap-4 text-sm mb-6' }, [
              [h('dt', { class: 'font-semibold text-gray-700' }, 'Domain'), h('dd', { class: 'text-gray-900' }, adConfig.value.domain_name || '—')],
              [h('dt', { class: 'font-semibold text-gray-700' }, 'NetBIOS Name'), h('dd', { class: 'text-gray-900' }, adConfig.value.netbios_name || '—')],
              [h('dt', { class: 'font-semibold text-gray-700' }, 'Base DN'), h('dd', { class: 'text-gray-900' }, adConfig.value.base_dn || '—')],
              [h('dt', { class: 'font-semibold text-gray-700' }, 'TLS Mode'), h('dd', { class: 'text-gray-900' }, adConfig.value.tls_mode || '—')],
              [h('dt', { class: 'font-semibold text-gray-700' }, 'Revalidation Interval'), h('dd', { class: 'text-gray-900' }, `${adConfig.value.revalidation_interval_minutes || 15} minutes`)],
              [h('dt', { class: 'font-semibold text-gray-700' }, 'Grace Period'), h('dd', { class: 'text-gray-900' }, `${adConfig.value.grace_period_minutes || 60} minutes`)],
            ]),
            h('div', { class: 'space-x-2' }, [
              h('button', {
                onClick: () => (editMode.value = true),
                class: 'px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700',
              }, 'Edit'),
              h('button', {
                onClick: handleTestConnection,
                disabled: testLoading.value,
                class: 'px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400',
              }, testLoading.value ? 'Testing...' : 'Test Connection'),
              h('button', {
                onClick: handleToggleEnabled,
                disabled: formLoading.value,
                class: adEnabled.value
                  ? 'px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400'
                  : 'px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400',
              }, adEnabled.value ? 'Disable AD' : 'Enable AD'),
              h('button', {
                onClick: handleDeleteConfig,
                disabled: formLoading.value,
                class: 'px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:bg-gray-400',
              }, 'Remove Configuration'),
            ]),
          ]),

          // Test results
          testResults.value && h('div', { class: 'bg-blue-50 p-6 rounded-lg border border-blue-200' }, [
            h('h3', { class: 'text-lg font-bold mb-4 text-blue-900' }, 'Connection Test Results'),
            h('div', { class: 'space-y-2 text-sm' }, [
              testResults.value.controllers && h('div', { class: 'space-y-1' }, [
                h('strong', 'Domain Controllers:'),
                testResults.value.controllers.map((ctrl) =>
                  h('p', { class: 'ml-4' }, `${ctrl.hostname}: ${ctrl.status}`)
                ),
              ]),
              testResults.value.service_account && h('p', [
                h('strong', 'Service Account: '),
                testResults.value.service_account.status,
              ]),
            ]),
          ]),

          testError.value && h('div', { class: 'bg-red-50 p-4 rounded-lg border border-red-200 text-red-800' }, testError.value),

          // Guidance section
          h('div', { class: 'bg-yellow-50 p-6 rounded-lg border border-yellow-200' }, [
            h('h3', { class: 'text-lg font-bold text-yellow-900 mb-2' }, 'Lockout Threshold Guidance'),
            h('p', { class: 'text-sm text-yellow-800 mb-2' },
              'The AD throttling limit (default 3 failures per identifier per 15 minutes) must stay below ' +
              'your domain\'s lockout threshold to prevent denial-of-service via failed sign-in attempts.'
            ),
            h('p', { class: 'text-sm text-yellow-800' },
              'Common domain defaults: 5 failed attempts within 30 minutes causes lockout. ' +
              'Adjust the throttling limit if your domain uses a stricter threshold.'
            ),
          ]),
        ]),
      ]);
  },
};
