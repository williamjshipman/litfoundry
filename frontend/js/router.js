/**
 * In-house History API router for LitFoundry SPA.
 * 
 * Features:
 * - Path-based routing with parameters
 * - Route guards for auth and admin checks
 * - Server fallback for deep links
 * - No dependencies (no vue-router, no import maps)
 */

/**
 * Route definition
 */
class Route {
  constructor(path, component, options = {}) {
    this.path = path;
    this.pattern = this.pathToPattern(path);
    this.component = component;
    this.guard = options.guard || null;
    this.props = options.props || {};
  }

  /**
   * Convert path like "/projects/:id" to a regex pattern
   */
  pathToPattern(path) {
    const segments = path.split('/').filter(Boolean);
    const pattern = segments.map(segment => {
      if (segment.startsWith(':')) {
        return `([^/]+)`;
      }
      return segment;
    }).join('/');
    return new RegExp(`^/${pattern}/?$`);
  }

  /**
   * Extract parameters from a path
   */
  match(path) {
    const match = this.pattern.exec(path);
    if (!match) return null;

    const params = {};
    const pathSegments = path.split('/').filter(Boolean);
    const defSegments = this.path.split('/').filter(Boolean);

    for (let i = 0; i < defSegments.length; i++) {
      if (defSegments[i].startsWith(':')) {
        const paramName = defSegments[i].slice(1);
        params[paramName] = pathSegments[i];
      }
    }

    return params;
  }
}

/**
 * Router class
 */
export class Router {
  constructor() {
    this.routes = [
      new Route('/', () => h('div', 'Home Page'), {}),
      new Route('/sign-in', () => h('div', 'Sign In'), {}),
      new Route('/not-found', () => h('div', 'Page Not Found'), {}),
    ];
    this.currentPath = window.location.pathname;
  }

  /**
   * Register a route
   */
  register(path, component, options = {}) {
    this.routes.push(new Route(path, component, options));
  }

  /**
   * Initialize router with history popstate listener
   */
  async init() {
    // Listen for back/forward button
    window.addEventListener('popstate', () => this.render());

    // Listen for link clicks
    document.addEventListener('click', (e) => {
      if (e.target.tagName === 'A' && e.target.href.startsWith(window.location.origin)) {
        e.preventDefault();
        const path = e.target.href.replace(window.location.origin, '');
        this.navigate(path);
      }
    });

    // Initial render
    await this.render();
  }

  /**
   * Navigate to a path
   */
  async navigate(path) {
    this.currentPath = path;
    window.history.pushState(null, '', path);
    await this.render();
  }

  /**
   * Render the current route
   */
  async render() {
    const path = window.location.pathname;
    this.currentPath = path;

    // Find matching route
    let route = null;
    let params = null;

    for (const r of this.routes) {
      const p = r.match(path);
      if (p !== null) {
        route = r;
        params = p;
        break;
      }
    }

    if (!route) {
      route = this.routes.find(r => r.path === '/not-found');
    }

    // Run guard if present
    if (route.guard) {
      const allowed = await route.guard(params);
      if (!allowed) {
        // Redirect to sign-in
        return this.navigate('/sign-in');
      }
    }

    // Render component
    const container = document.getElementById('router-view');
    if (container) {
      const component = route.component;
      // For now, just show a message
      container.innerHTML = `<div class="p-4">${route.path}</div>`;
    }
  }

  /**
   * Create a safe link to a route
   */
  createLink(path, text) {
    const a = document.createElement('a');
    a.href = path;
    a.textContent = text;
    a.classList.add('router-link');
    return a;
  }
}

// Export default instance
export default new Router();
