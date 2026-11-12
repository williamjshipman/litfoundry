/**
 * Playwright test utilities for LitFoundry.
 * 
 * Includes:
 * - CSP violation collector
 * - Offline mode testing
 * - Common fixtures and helpers
 */

import { test as base, expect } from '@playwright/test';

/**
 * CSP violation collector
 * Captures all CSP violations during test
 */
class CSPViolationCollector {
  constructor(page) {
    this.page = page;
    this.violations = [];
  }

  async start() {
    await this.page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('CSP')) {
        this.violations.push(msg.text());
      }
    });

    // Listen for CSP violation events
    await this.page.evaluateHandle(() => {
      window.cspViolations = [];
      document.addEventListener('securitypolicyviolation', (e) => {
        window.cspViolations.push({
          blockedURI: e.blockedURI,
          violatedDirective: e.violatedDirective,
          originalPolicy: e.originalPolicy,
        });
      });
    });
  }

  async getViolations() {
    const clientViolations = await this.page.evaluate(() => window.cspViolations || []);
    return [...this.violations, ...clientViolations];
  }

  async assertNoViolations() {
    const violations = await this.getViolations();
    expect(violations).toHaveLength(0);
  }
}

/**
 * Offline mode simulator
 */
class OfflineSimulator {
  constructor(page) {
    this.page = page;
  }

  async goOnline() {
    await this.page.context().setOffline(false);
  }

  async goOffline() {
    await this.page.context().setOffline(true);
  }

  async testOfflineExperience() {
    // Navigate to app
    await this.page.goto('http://localhost:5080');

    // Go offline
    await this.goOffline();

    // Try to perform an action
    const button = await this.page.$('button[data-action="sync"]');
    if (button) {
      await button.click();
      
      // Should show error or offline state
      const error = await this.page.$('.error-message, [data-offline="true"]');
      expect(error).toBeTruthy();
    }

    // Go back online
    await this.goOnline();
  }
}

/**
 * Extended test fixture with CSP and offline utilities
 */
export const test = base.extend({
  cspCollector: async ({ page }, use) => {
    const collector = new CSPViolationCollector(page);
    await collector.start();
    await use(collector);
    
    // Verify no CSP violations occurred
    await collector.assertNoViolations();
  },

  offlineSimulator: async ({ context }, use) => {
    const simulator = new OfflineSimulator(context);
    await use(simulator);
  },
});

export { expect };

/**
 * Common test helpers
 */
export const helpers = {
  /**
   * Navigate to app and wait for ready
   */
  async navigateToApp(page) {
    await page.goto('http://localhost:5080');
    await page.waitForLoadState('networkidle');
  },

  /**
   * Check for accessibility issues
   */
  async checkAccessibility(page) {
    // This would integrate with axe-core
    // For now, just check basic ARIA attributes
    const buttons = await page.locator('button').all();
    for (const button of buttons) {
      const ariaLabel = await button.getAttribute('aria-label');
      const text = await button.textContent();
      
      // Button should have either aria-label or text content
      expect(ariaLabel || text).toBeTruthy();
    }
  },

  /**
   * Verify keyboard navigation
   */
  async verifyKeyboardNavigation(page) {
    // Tab through interactive elements
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => {
      return {
        tag: document.activeElement?.tagName,
        id: document.activeElement?.id,
        ariaLabel: document.activeElement?.getAttribute('aria-label'),
      };
    });

    expect(['BUTTON', 'A', 'INPUT']).toContain(focused.tag);
  },

  /**
   * Wait for API response
   */
  async waitForApiResponse(page, pattern) {
    return page.waitForResponse(
      response => response.url().includes(pattern) && response.status() === 200
    );
  },

  /**
   * Mock API response
   */
  async mockApiResponse(page, pattern, responseData) {
    await page.route(pattern, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(responseData),
      });
    });
  },
};
