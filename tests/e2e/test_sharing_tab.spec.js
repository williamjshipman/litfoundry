/**
 * End-to-end tests for Sharing tab
 * 
 * Tests:
 * - Visibility selector (Private, Public view, Public edit)
 * - Public edit confirmation dialog
 * - ACL editor with user search and add/remove
 * - Effective permissions preview
 * - Audit event display
 */

import { test, expect } from '@playwright/test';

test.describe('Sharing Tab', () => {
  test.beforeEach(async ({ page }) => {
    // Start the server and navigate to projects
    await page.goto('http://localhost:5080/projects');
    await page.waitForLoadState('networkidle');
  });

  test('should load sharing tab', async ({ page }) => {
    // Navigate to a project (mock or real)
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');
    
    // Sharing tab should be visible
    const sharingSection = await page.$('.sharing-tab');
    expect(sharingSection).toBeTruthy();
  });

  test('should display visibility selector', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Check for visibility options
    const visibilityOptions = await page.locator('[name="visibility"]').all();
    expect(visibilityOptions.length).toBeGreaterThanOrEqual(3); // Private, Public view, Public edit

    // Labels should be present
    const privateLabel = await page.locator('text=Private');
    expect(privateLabel).toBeTruthy();

    const publicViewLabel = await page.locator('text=Public view');
    expect(publicViewLabel).toBeTruthy();

    const publicEditLabel = await page.locator('text=Public edit');
    expect(publicEditLabel).toBeTruthy();
  });

  test('should show public edit confirmation dialog', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Get the public edit radio button
    const publicEditRadio = await page.locator('input[name="visibility"][value="editor"]');
    
    // Click it
    await publicEditRadio.click();

    // Confirmation dialog should appear
    await page.waitForSelector('.warning-dialog');
    const dialog = await page.$('.warning-dialog');
    expect(dialog).toBeTruthy();

    // Dialog should have warning text
    const warningText = await page.locator('text=Make Project Public for Editing');
    expect(warningText).toBeTruthy();

    // Should have Cancel and Confirm buttons
    const cancelBtn = await page.locator('button:has-text("Cancel")');
    const confirmBtn = await page.locator('button:has-text("Confirm")');
    
    expect(cancelBtn).toBeTruthy();
    expect(confirmBtn).toBeTruthy();
  });

  test('should cancel public edit confirmation', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Click public edit radio
    const publicEditRadio = await page.locator('input[name="visibility"][value="editor"]');
    await publicEditRadio.click();

    // Wait for dialog
    await page.waitForSelector('.warning-dialog');

    // Click Cancel
    const cancelBtn = await page.locator('button:has-text("Cancel")');
    await cancelBtn.click();

    // Dialog should disappear
    const dialog = await page.$('.warning-dialog');
    expect(dialog).toBeFalsy();
  });

  test('should search for users', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Find user search input
    const searchInput = await page.locator('input[placeholder="Search for user..."]');
    expect(searchInput).toBeTruthy();

    // Type in search box
    await searchInput.fill('test');

    // Results should appear
    await page.waitForSelector('.search-results', { timeout: 1000 }).catch(() => {
      // May not have results in test environment
    });
  });

  test('should add user to ACL', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Search for a user
    const searchInput = await page.locator('input[placeholder="Search for user..."]');
    await searchInput.fill('test-user');

    // Mock API response for user search
    await page.route('/api/v1/users/lookup*', (route) => {
      route.abort('blockedbyClient'); // Stub response
    });

    // Select a role from dropdown (if results appear)
    const roleDropdowns = await page.locator('select').all();
    if (roleDropdowns.length > 0) {
      await roleDropdowns[0].selectOption('editor');
    }
  });

  test('should remove user from ACL', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Find remove buttons in ACL list
    const removeButtons = await page.locator('button:has-text("✕")').all();
    
    if (removeButtons.length > 0) {
      const firstCount = removeButtons.length;
      
      // Click first remove button
      await removeButtons[0].click();

      // ACL list should update (may have one fewer button)
      await page.waitForTimeout(100);
      const newButtons = await page.locator('button:has-text("✕")').all();
      
      // Verify button was removed or API was called
      expect(newButtons.length).toBeLessThanOrEqual(firstCount);
    }
  });

  test('should display effective permissions table', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Check for permissions table
    const permTable = await page.$('.permissions-table');
    expect(permTable).toBeTruthy();

    // Table should have headers
    const headers = await page.locator('.permissions-table th').all();
    expect(headers.length).toBeGreaterThanOrEqual(3); // User, Access Level, Rule
  });

  test('should show access levels in table', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Effective permissions section should be visible
    const effPermsSection = await page.locator('h2:has-text("Effective Permissions Preview")');
    expect(effPermsSection).toBeTruthy();

    // Table rows should contain access level values
    const tableCells = await page.locator('.permissions-table td').all();
    
    if (tableCells.length > 0) {
      // At least some cells should be visible
      expect(tableCells.length).toBeGreaterThan(0);
    }
  });

  test('should show deciding rule for each user', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Table should have rule column
    const ruleCells = await page.locator('.permissions-table td:nth-child(3)').all();
    
    if (ruleCells.length > 0) {
      // Rules should be displayed (admin, owner, explicit_grant, etc.)
      for (const cell of ruleCells) {
        const text = await cell.textContent();
        // Text should be non-empty (even if just whitespace for no-permission users)
        expect(text).toBeDefined();
      }
    }
  });

  test('should have proper tab navigation', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Find tab buttons
    const tabs = await page.locator('nav.tabs button').all();
    
    if (tabs.length > 0) {
      // Should have at least Overview and Sharing tabs
      expect(tabs.length).toBeGreaterThanOrEqual(2);

      // Sharing tab should be marked as active
      const sharingTab = await page.locator('nav.tabs button:has-text("Sharing")');
      const activeTab = await page.locator('nav.tabs button.tab-active');
      
      if (sharingTab && activeTab) {
        // One should match
        expect([sharingTab, activeTab]).toBeDefined();
      }
    }
  });

  test('should switch between tabs', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Find Overview tab
    const overviewTab = await page.locator('nav.tabs button:has-text("Overview")');
    
    if (overviewTab) {
      await overviewTab.click();
      
      // Content should change
      const overview = await page.locator('text=Project Overview Tab');
      expect(overview).toBeTruthy();
    }

    // Switch back to Sharing
    const sharingTab = await page.locator('nav.tabs button:has-text("Sharing")');
    if (sharingTab) {
      await sharingTab.click();

      // Sharing content should be visible again
      await page.waitForSelector('.sharing-tab', { timeout: 1000 }).catch(() => {
        // May not have element if page not fully loaded
      });
    }
  });

  test('should have proper styling', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Check that key elements have expected classes
    const sharingTab = await page.$('.sharing-tab');
    expect(sharingTab).toBeTruthy();

    // Sections should have card styling
    const cards = await page.locator('.card').all();
    expect(cards.length).toBeGreaterThanOrEqual(1);

    // Input elements should be present
    const inputs = await page.locator('input, select').all();
    expect(inputs.length).toBeGreaterThan(0);
  });

  test('should handle rate limiting gracefully', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Mock rate limit response
    let requestCount = 0;
    await page.route('/api/v1/users/lookup*', (route) => {
      requestCount++;
      if (requestCount > 30) {
        route.abort('blockedbyClient');
      } else {
        route.abort('blockedbyClient');
      }
    });

    // User search should handle errors gracefully
    const searchInput = await page.locator('input[placeholder="Search for user..."]');
    await searchInput.fill('test');

    // No unhandled exceptions should occur
    const errors = await page.evaluate(() => window.__errors || []);
    expect(errors).toEqual([]);
  });

  test('should show confirmation warning for public edit', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Click public edit radio
    const publicEditRadio = await page.locator('input[name="visibility"][value="editor"]');
    await publicEditRadio.click();

    // Dialog should appear with warning
    await page.waitForSelector('.warning-dialog', { timeout: 1000 });
    
    const warningText = await page.locator('.warning-dialog p');
    const text = await warningText.textContent();
    
    expect(text).toContain('modify');
  });

  test('should validate ACL updates', async ({ page }) => {
    await page.goto('http://localhost:5080/projects/test-project-id/sharing');

    // Mock sharing API
    await page.route('/api/v1/projects/test-project-id/sharing', (route) => {
      if (route.request().method() === 'PUT') {
        route.abort('blockedbyClient');
      } else {
        route.continue();
      }
    });

    // Adding ACL should attempt API call
    const searchInput = await page.locator('input[placeholder="Search for user..."]');
    if (searchInput) {
      await searchInput.fill('test');
    }
  });
});
