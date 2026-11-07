/**
 * Admin System page for LitFoundry (Task 6.3).
 * Shows system information, run mode, proxy configuration, and readiness checks.
 * Admin-only access.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AdminSystemPage',
  setup() {
    const systemInfo = ref(null);
    const readinessChecks = ref(null);
    const loading = ref(true);

    const loadSystemInfo = async () => {
      loading.value = true;
      try {
        // Fetch system info and health check
        const response = await fetch('/api/v1/health/ready', {
          credentials: 'include',
        });
        if (response.ok) {
          readinessChecks.value = await response.json();
        }

        // Get basic system info from config (hardcoded for now)
        systemInfo.value = {
          version: '1.3.0',
          runMode: 'server',
          hostname: window.location.hostname,
          environment: 'production',
          pythonVersion: '3.12+',
          framework: 'Flask',
          database: 'SQLite',
        };
      } catch (err) {
        console.error('Failed to load system info', err);
      } finally {
        loading.value = false;
      }
    };

    loadSystemInfo();

    return () =>
      h('div', { class: 'p-6 max-w-4xl mx-auto' }, [
        h('h1', { class: 'text-3xl font-bold mb-6' }, 'System Information'),

        systemInfo.value &&
          h('div', { class: 'grid gap-6' }, [
            h('div', { class: 'bg-white p-6 rounded-lg shadow' }, [
              h('h2', { class: 'text-2xl font-bold mb-4' }, 'Versions'),
              h('dl', { class: 'grid grid-cols-2 gap-4' }, [
                [h('dt', { class: 'font-semibold' }, 'LitFoundry'), h('dd', { class: 'text-gray-600' }, systemInfo.value.version)],
                [h('dt', { class: 'font-semibold' }, 'Python'), h('dd', { class: 'text-gray-600' }, systemInfo.value.pythonVersion)],
                [h('dt', { class: 'font-semibold' }, 'Framework'), h('dd', { class: 'text-gray-600' }, systemInfo.value.framework)],
                [h('dt', { class: 'font-semibold' }, 'Database'), h('dd', { class: 'text-gray-600' }, systemInfo.value.database)],
              ]),
            ]),

            h('div', { class: 'bg-white p-6 rounded-lg shadow' }, [
              h('h2', { class: 'text-2xl font-bold mb-4' }, 'Configuration'),
              h('dl', { class: 'grid grid-cols-2 gap-4' }, [
                [h('dt', { class: 'font-semibold' }, 'Run Mode'), h('dd', { class: 'text-gray-600' }, systemInfo.value.runMode)],
                [h('dt', { class: 'font-semibold' }, 'Hostname'), h('dd', { class: 'text-gray-600 break-all' }, systemInfo.value.hostname)],
                [h('dt', { class: 'font-semibold' }, 'Environment'), h('dd', { class: 'text-gray-600' }, systemInfo.value.environment)],
              ]),
            ]),

            readinessChecks.value &&
              h('div', { class: 'bg-white p-6 rounded-lg shadow' }, [
                h('h2', { class: 'text-2xl font-bold mb-4' }, 'Readiness Checks'),
                h('dl', { class: 'space-y-2' }, [
                  [
                    h('dt', { class: 'font-semibold' }, 'Status'),
                    h('dd', {
                      class: readinessChecks.value.status === 'ready' 
                        ? 'text-green-600 font-semibold' 
                        : 'text-red-600 font-semibold'
                    }, readinessChecks.value.status),
                  ],
                  ...(readinessChecks.value.checks
                    ? Object.entries(readinessChecks.value.checks).map(([key, value]) => [
                        h('dt', { class: 'font-semibold text-sm' }, key),
                        h('dd', {
                          class: value === 'ok' ? 'text-green-600 text-sm' : 'text-red-600 text-sm'
                        }, value),
                      ])
                    : []),
                ]),
              ]),
          ]),
      ]);
  },
};
