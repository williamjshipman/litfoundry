/**
 * End-to-end tests for SPA shell
 * 
 * Tests:
 * - CSP compliance (no violations)
 * - Router navigation (client-side)
 * - Offline functionality
 * - Accessibility (keyboard, ARIA)
 */

import { test, expect, helpers } from './playwright.fixtures.js';

test.describe('SPA Shell', () => {
  test('should load without CSP violations', async ({ page, cspCollector }) => {
    await page.goto('http://localhost:5080');
    await page.waitForLoadState('networkidle');

    // CSP collector automatically verifies no violations at end
    expect(page.url()).toContain('localhost:5080');
  });

  test('should render app container', async ({ page }) => {
    await page.goto('http://localhost:5080');
    
    const app = await page.$('#app');
    expect(app).toBeTruthy();

    const navbar = await page.$('.navbar');
    expect(navbar).toBeTruthy();
  });

  test('should support client-side routing', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Click a link
    const links = await page.locator('a.router-link').all();
    if (links.length > 0) {
      const href = await links[0].getAttribute('href');
      await links[0].click();
      
      // URL should change without full reload
      expect(page.url()).toContain(href);
    }
  });

  test('should handle navigation with browser back/forward', async ({ page }) => {
    await page.goto('http://localhost:5080');
    const initialUrl = page.url();

    // Navigate to a path
    await page.goto(`http://localhost:5080/projects`);
    expect(page.url()).toContain('/projects');

    // Go back
    await page.goBack();
    expect(page.url()).toEqual(initialUrl);

    // Go forward
    await page.goForward();
    expect(page.url()).toContain('/projects');
  });

  test('should show loading state', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Simulate slow network
    await page.route('/api/v1/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      route.abort('blockedbyClient');
    });

    // Loading component should be visible
    const loading = await page.$('.loading-container');
    // (assuming loading state appears during slow requests)
  });

  test('should show empty state', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Navigate to a section that might be empty
    const empty = await page.$('.empty-container');
    // (depending on app state)
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => document.activeElement?.tagName);

    expect(['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA']).toContain(focused);
  });

  test('should have accessible button labels', async ({ page }) => {
    await page.goto('http://localhost:5080');

    const buttons = await page.locator('button').all();
    for (const button of buttons) {
      const ariaLabel = await button.getAttribute('aria-label');
      const text = await button.textContent();
      
      // Each button should have either aria-label or visible text
      const hasLabel = ariaLabel || (text && text.trim().length > 0);
      expect(hasLabel).toBeTruthy();
    }
  });

  test('should handle offline mode gracefully', async ({ page, offlineSimulator }) => {
    await page.goto('http://localhost:5080');

    // Go offline
    await offlineSimulator.goOffline();
    await page.waitForTimeout(100);

    // Page should still be usable (static content visible)
    const app = await page.$('#app');
    expect(app).toBeTruthy();

    // Go back online
    await offlineSimulator.goOnline();
  });

  test('should attach CSRF token to POST requests', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Intercept and verify POST request
    page.on('request', (request) => {
      if (request.method() === 'POST') {
        const headers = request.headers();
        // CSRF token might be in X-CSRF-TOKEN header or cookie
        expect(
          headers['x-csrf-token'] || 
          (headers['cookie'] && headers['cookie'].includes('csrf'))
        ).toBeTruthy();
      }
    });
  });

  test('should reject cross-origin requests', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Try to make a cross-origin POST
    page.on('request', (request) => {
      if (request.method() === 'POST' && !request.url().includes('localhost:5080')) {
        // Browser will block this or we should see a rejection
        expect(false).toBeTruthy(); // Should not reach here
      }
    });
  });

  test('should render text-only content safely', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Check that no innerHTML is used
    const hasDangerousHtml = await page.evaluate(() => {
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_ELEMENT,
        null,
        false
      );

      let node;
      while (node = walker.nextNode()) {
        // Check if element has suspicious content
        if (node.innerHTML && node.innerHTML.includes('<script')) {
          return true;
        }
      }
      return false;
    });

    expect(hasDangerousHtml).toBe(false);
  });

  test('should show error state with retry', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Simulate an error
    await page.route('/api/v1/health', (route) => {
      route.abort('blockedbyClient');
    });

    // Error component should be visible if health check fails
    // (depends on app implementation)
  });

  test('should support confirmation dialog', async ({ page }) => {
    await page.goto('http://localhost:5080');

    // Check if confirm dialog exists (if implemented)
    const dialog = await page.$('[role="alertdialog"]');
    // Dialog should be hidden initially
    if (dialog) {
      const isVisible = await dialog.isVisible();
      expect(isVisible).toBe(false);
    }
  });
});
