/**
 * LitFoundry SPA main entry point.
 * 
 * Initializes Vue runtime, router, API client, and mounts the app.
 */

import { createApp, h } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';
import { Router } from '/frontend/js/router.js';
import { apiClient } from '/frontend/js/api-client.js';

/**
 * Root component - the SPA shell
 */
function AppShell() {
  return h('div', { class: 'app-container' }, [
    h('header', { class: 'navbar' }, [
      h('h1', 'LitFoundry'),
    ]),
    h('main', { class: 'main-content' }, [
      h('div', { id: 'router-view' }),
    ]),
  ]);
}

/**
 * Initialize and mount the application
 */
async function main() {
  // Create Vue app
  const app = createApp({
    setup() {
      return () => h(AppShell);
    },
  });

  // Make API client available globally
  app.config.globalProperties.$api = apiClient;

  // Mount to DOM
  const container = document.getElementById('app');
  if (!container) {
    console.error('App container (#app) not found');
    return;
  }

  const instance = app.mount(container);

  // Initialize router
  const router = new Router();
  await router.init();
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', main);
} else {
  main().catch(err => {
    console.error('Failed to initialize app:', err);
  });
}
