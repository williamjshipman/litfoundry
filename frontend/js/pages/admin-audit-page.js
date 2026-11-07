/**
 * Admin Audit Events page for LitFoundry (Task 5.3).
 * Displays audit trail of all sensitive admin actions.
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AdminAuditPage',
  setup() {
    const events = ref([]);
    const loading = ref(false);
    const actionFilter = ref('');
    const resourceTypeFilter = ref('');

    const loadEvents = async () => {
      loading.value = true;
      try {
        let url = '/api/v1/admin/audit-events?limit=100';
        if (actionFilter.value) url += `&action=${actionFilter.value}`;
        if (resourceTypeFilter.value) url += `&resource_type=${resourceTypeFilter.value}`;

        const response = await fetch(url, { credentials: 'include' });
        if (response.ok) {
          const data = await response.json();
          events.value = data.events || [];
        }
      } catch (err) {
        console.error('Failed to load audit events', err);
      } finally {
        loading.value = false;
      }
    };

    loadEvents();

    return () =>
      h('div', { class: 'p-6 max-w-6xl mx-auto' }, [
        h('h1', { class: 'text-3xl font-bold mb-6' }, 'Audit Log'),

        h('div', { class: 'mb-6 flex gap-4' }, [
          h('input', {
            type: 'text',
            placeholder: 'Filter by action',
            value: actionFilter.value,
            onInput: (e) => { actionFilter.value = e.target.value; loadEvents(); },
            class: 'px-3 py-2 border rounded',
          }),
          h('input', {
            type: 'text',
            placeholder: 'Filter by resource type',
            value: resourceTypeFilter.value,
            onInput: (e) => { resourceTypeFilter.value = e.target.value; loadEvents(); },
            class: 'px-3 py-2 border rounded',
          }),
        ]),

        h('div', { class: 'overflow-x-auto' }, [
          h('table', { class: 'w-full border text-sm' }, [
            h('thead', {}, [
              h('tr', { class: 'bg-gray-200' }, [
                h('th', { class: 'px-4 py-2 text-left' }, 'Timestamp'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Action'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Resource'),
                h('th', { class: 'px-4 py-2 text-left' }, 'Status'),
                h('th', { class: 'px-4 py-2 text-left' }, 'IP Address'),
              ]),
            ]),
            h('tbody', {}, events.value.map((event) =>
              h('tr', { key: event.id, class: 'border-b' }, [
                h('td', { class: 'px-4 py-2' }, new Date(event.created_at).toLocaleString()),
                h('td', { class: 'px-4 py-2' }, event.action),
                h('td', { class: 'px-4 py-2' }, `${event.resource_type} ${event.resource_id || ''}`),
                h('td', { class: 'px-4 py-2' }, 
                  h('span', { class: event.status === 'success' ? 'text-green-600' : 'text-red-600' },
                    event.status,
                  ),
                ),
                h('td', { class: 'px-4 py-2' }, event.ip_address),
              ]),
            )),
          ]),
        ]),
      ]);
  },
};
