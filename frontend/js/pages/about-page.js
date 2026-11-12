/**
 * About page for LitFoundry (Task 6.2).
 * Shows application information, version, license, and admin trust disclosure.
 */

import { h } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

export default {
  name: 'AboutPage',
  setup() {
    return () =>
      h('div', { class: 'min-h-screen bg-gray-50 py-12 px-4' }, [
        h('div', { class: 'max-w-2xl mx-auto' }, [
          h('div', { class: 'bg-white p-8 rounded-lg shadow' }, [
            h('h1', { class: 'text-4xl font-bold text-gray-900 mb-2' }, 'LitFoundry'),
            h('p', { class: 'text-xl text-gray-600 mb-8' }, 
              'Systematic Literature Review Platform',
            ),

            h('section', { class: 'mb-8' }, [
              h('h2', { class: 'text-2xl font-bold mb-4' }, 'About'),
              h('p', { class: 'text-gray-700 mb-4' },
                'LitFoundry is an open-source application for systematic literature reviews, ',
                'PRISMA workflows, and bibliometric analysis. It helps researchers manage the ',
                'complete literature review process from search to synthesis.',
              ),
            ]),

            h('section', { class: 'mb-8' }, [
              h('h2', { class: 'text-2xl font-bold mb-4' }, 'Information'),
              h('dl', { class: 'space-y-3' }, [
                [h('dt', { class: 'font-semibold' }, 'Version'), h('dd', { class: 'text-gray-600' }, '1.3.0')],
                [h('dt', { class: 'font-semibold' }, 'Status'), h('dd', { class: 'text-gray-600' }, 'Beta')],
                [h('dt', { class: 'font-semibold' }, 'Homepage'), h('dd', { class: 'text-blue-600' }, 
                  h('a', { href: '#', target: '_blank' }, 'github.com/litfoundry/litfoundry'),
                )],
              ]),
            ]),

            h('section', { class: 'mb-8' }, [
              h('h2', { class: 'text-2xl font-bold mb-4' }, 'License'),
              h('p', { class: 'text-gray-700 mb-2' },
                'LitFoundry is licensed under the GNU General Public License v3.0 (GPLv3).',
              ),
              h('p', { class: 'text-gray-700' },
                'You are free to use, modify, and distribute this software under the terms of ',
                'the GPLv3 license. See LICENSE file for details.',
              ),
            ]),

            h('section', { class: 'bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded' }, [
              h('h2', { class: 'text-xl font-bold mb-2 text-yellow-900' }, '⚠️ Administrator Trust Model'),
              h('p', { class: 'text-yellow-800' },
                'LitFoundry operates on a trust model where administrators are fully trusted. ',
                'Administrators have complete access to all data and system configuration. ',
                'Only grant administrator access to trusted individuals.',
              ),
            ]),
          ]),
        ]),
      ]);
  },
};
