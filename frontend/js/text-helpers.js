/**
 * Text-only rendering helpers for LitFoundry.
 * 
 * Enforces text-only content (no innerHTML, no unsafe HTML).
 * Use these helpers to safely render user-generated or untrusted content.
 */

import { h } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

/**
 * Safe text helper - renders plain text only
 * @param {string} text - Plain text to render
 * @returns {VNode} Vue render function node
 */
export function text(text) {
  // Return plain string; Vue will escape it
  return String(text || '');
}

/**
 * Safe link helper - renders text link only (no href if not same-origin)
 * @param {string} href - URL to link to (must be relative or same-origin)
 * @param {string} text - Link text
 * @returns {VNode} Vue render function node
 */
export function safeLink(href, linkText) {
  // Verify same-origin
  if (!href.startsWith('/') && !href.startsWith(window.location.origin)) {
    console.warn(`Cross-origin link blocked: ${href}`);
    return h('span', linkText);
  }

  return h('a', {
    href,
    class: 'text-primary hover:underline',
    // Ensure no inline event handlers
    onClick: (e) => {
      // Let Vue router handle it, or browser will navigate
      // No need for special handling here
    },
  }, linkText);
}

/**
 * Safe code helper - renders code text with escaping
 * @param {string} code - Code string to render
 * @returns {VNode} Vue render function node
 */
export function safeCode(code) {
  return h('code', {
    class: 'bg-gray-100 px-1 py-0.5 rounded font-mono text-sm',
  }, String(code || ''));
}

/**
 * Safe list helper - renders a list of text items
 * @param {Array<string>} items - List items (text only)
 * @param {string} tag - 'ul' or 'ol' (default: 'ul')
 * @returns {VNode} Vue render function node
 */
export function safeList(items = [], tag = 'ul') {
  return h(tag, { class: 'list-' + tag === 'ol' ? 'decimal' : 'disc' + ' ml-4' }, 
    items.map(item => h('li', String(item)))
  );
}

/**
 * Safe paragraph helper - renders text in a paragraph
 * @param {string} text - Paragraph text
 * @returns {VNode} Vue render function node
 */
export function safeParagraph(text) {
  return h('p', { class: 'text-base leading-6' }, String(text || ''));
}

/**
 * Safe heading helper - renders a heading with text only
 * @param {number} level - Heading level (1-6)
 * @param {string} text - Heading text
 * @returns {VNode} Vue render function node
 */
export function safeHeading(level, text) {
  const tag = `h${Math.min(Math.max(level, 1), 6)}`;
  const sizeClass = {
    h1: 'text-3xl',
    h2: 'text-2xl',
    h3: 'text-xl',
    h4: 'text-lg',
    h5: 'text-base',
    h6: 'text-sm',
  }[tag] || 'text-base';

  return h(tag, { class: `font-semibold ${sizeClass}` }, String(text || ''));
}

/**
 * Safe table helper - renders a table from data
 * @param {Array<string>} headers - Column headers (text only)
 * @param {Array<Array<string>>} rows - Table rows (text only)
 * @returns {VNode} Vue render function node
 */
export function safeTable(headers = [], rows = []) {
  return h('table', { class: 'w-full border-collapse border border-gray-300' }, [
    h('thead', [
      h('tr', headers.map(header => h('th', { class: 'border border-gray-300 p-2 bg-gray-100 text-left font-semibold' }, String(header)))),
    ]),
    h('tbody', rows.map(row => 
      h('tr', row.map(cell => h('td', { class: 'border border-gray-300 p-2' }, String(cell))))
    )),
  ]);
}

/**
 * Lint rule: Forbid innerHTML
 * 
 * This is a structural constraint enforced by code review:
 * - Never use v-html (not available in render functions anyway)
 * - Never use dangerouslySetInnerHTML (doesn't exist in Vue)
 * - Never access element.innerHTML in event handlers
 * - Always use render functions with text content, not string templates
 * 
 * Lint configuration (for external linters like ESLint):
 * ```json
 * {
 *   "rules": {
 *     "vue/no-v-html": "error",
 *     "no-restricted-properties": [
 *       "error",
 *       {
 *         "object": "Element",
 *         "property": "innerHTML",
 *         "message": "Use safe rendering helpers instead"
 *       }
 *     ]
 *   }
 * }
 * ```
 */

/**
 * Validate that content is safe (text-only, no markup)
 * @param {string} content - Content to validate
 * @returns {boolean} True if content is text-only
 */
export function isTextOnly(content) {
  if (typeof content !== 'string') return false;
  // Check for HTML-like patterns (< followed by letters)
  return !/<\w/.test(content);
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} Escaped text safe for HTML
 */
export function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return String(text).replace(/[&<>"']/g, char => map[char]);
}
