/**
 * Admin Logs page for LitFoundry (Task 6.4).
 * Views application logs with filtering by level, process, and request_id.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AdminLogsPage',
  setup() {
    const logs = ref([]);
    const loading = ref(false);
    const levelFilter = ref('');
    const processFilter = ref('');
    const requestIdFilter = ref('');
    const autoRefresh = ref(true);

    const loadLogs = async () => {
      loading.value = true;
      try {
        let url = '/api/v1/admin/logs?limit=500';
        if (levelFilter.value) url += `&level=${levelFilter.value}`;
        if (processFilter.value) url += `&process=${processFilter.value}`;
        if (requestIdFilter.value) url += `&request_id=${requestIdFilter.value}`;

        const response = await fetch(url, { credentials: 'include' });
        if (response.ok) {
          const data = await response.json();
          logs.value = (data.logs || []).reverse(); // Most recent first
        }
      } catch (err) {
        console.error('Failed to load logs', err);
      } finally {
        loading.value = false;
      }
    };

    const getLevelColor = (level) => {
      const colors = {
        DEBUG: 'text-gray-500',
        INFO: 'text-blue-600',
        WARNING: 'text-yellow-600',
        ERROR: 'text-red-600',
        CRITICAL: 'text-red-900 font-bold',
      };
      return colors[level] || 'text-gray-600';
    };

    loadLogs();

    // Auto-refresh every 5 seconds if enabled
    if (autoRefresh.value) {
      const interval = setInterval(loadLogs, 5000);
      // Cleanup on unmount would happen here in a real component
    }

    return () =>
      h('div', { class: 'p-6 max-w-7xl mx-auto' }, [
        h('h1', { class: 'text-3xl font-bold mb-6' }, 'Application Logs'),

        h('div', { class: 'mb-6 flex gap-4 flex-wrap items-center' }, [
          h('input', {
            type: 'text',
            placeholder: 'Filter by level (DEBUG, INFO, WARNING, ERROR)',
            value: levelFilter.value,
            onInput: (e) => { levelFilter.value = e.target.value; loadLogs(); },
            class: 'px-3 py-2 border rounded flex-1 min-w-[200px]',
          }),
          h('input', {
            type: 'text',
            placeholder: 'Filter by process',
            value: processFilter.value,
            onInput: (e) => { processFilter.value = e.target.value; loadLogs(); },
            class: 'px-3 py-2 border rounded flex-1 min-w-[200px]',
          }),
          h('input', {
            type: 'text',
            placeholder: 'Filter by request_id',
            value: requestIdFilter.value,
            onInput: (e) => { requestIdFilter.value = e.target.value; loadLogs(); },
            class: 'px-3 py-2 border rounded flex-1 min-w-[200px]',
          }),
          h('label', { class: 'flex items-center gap-2 whitespace-nowrap' }, [
            h('input', {
              type: 'checkbox',
              checked: autoRefresh.value,
              onInput: (e) => { autoRefresh.value = e.target.checked; },
              class: 'w-4 h-4',
            }),
            'Auto-refresh',
          ]),
        ]),

        h('div', { class: 'bg-gray-900 rounded p-4 font-mono text-sm text-gray-100 overflow-x-auto max-h-96 overflow-y-auto' }, [
          logs.value.length > 0
            ? logs.value.map((log) =>
                h('div', 
                  { key: log.id || log.timestamp, class: 'mb-2 font-mono text-xs' },
                  h('span', { class: getLevelColor(log.level) }, 
                    `[${log.timestamp}] [${log.level}] [${log.process || 'main'}] ${log.request_id ? `[${log.request_id}] ` : ''}${log.message}`,
                  ),
                ),
              )
            : h('div', { class: 'text-gray-500' }, 'No logs found'),
        ]),
      ]);
  },
};
