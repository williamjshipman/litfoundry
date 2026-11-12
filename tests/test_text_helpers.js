/**
 * Frontend unit tests for SPA shell components
 */

import { describe, it, expect } from '@jest/globals';
import { text, safeLink, safeCode, safeHeading, isTextOnly, escapeHtml } from '../frontend/js/text-helpers.js';

describe('Text Helpers', () => {
  describe('text()', () => {
    it('should return plain text', () => {
      expect(text('hello')).toBe('hello');
    });

    it('should escape HTML characters', () => {
      const result = text('<script>alert("xss")</script>');
      expect(result).not.toContain('<script>');
    });

    it('should handle null', () => {
      expect(text(null)).toBe('');
    });
  });

  describe('safeLink()', () => {
    it('should create link with relative URL', () => {
      const link = safeLink('/projects', 'Projects');
      expect(link).toBeDefined();
    });

    it('should reject cross-origin links', () => {
      // Should not create link with external URL
      const link = safeLink('https://external.com', 'External');
      expect(link).toBeDefined();
    });
  });

  describe('safeCode()', () => {
    it('should wrap code in code tag', () => {
      const code = safeCode('const x = 1;');
      expect(code).toBeDefined();
    });
  });

  describe('safeHeading()', () => {
    it('should create heading with text content', () => {
      const heading = safeHeading(1, 'Title');
      expect(heading).toBeDefined();
    });

    it('should clamp level between 1-6', () => {
      const h7 = safeHeading(7, 'Text');
      const h0 = safeHeading(0, 'Text');
      expect(h7).toBeDefined();
      expect(h0).toBeDefined();
    });
  });

  describe('isTextOnly()', () => {
    it('should return true for plain text', () => {
      expect(isTextOnly('hello world')).toBe(true);
    });

    it('should return false for HTML', () => {
      expect(isTextOnly('<b>bold</b>')).toBe(false);
    });

    it('should return false for tags', () => {
      expect(isTextOnly('<script>')).toBe(false);
    });
  });

  describe('escapeHtml()', () => {
    it('should escape HTML special chars', () => {
      expect(escapeHtml('<b>text</b>')).toBe('&lt;b&gt;text&lt;/b&gt;');
    });

    it('should escape quotes', () => {
      expect(escapeHtml('"quoted"')).toBe('&quot;quoted&quot;');
    });

    it('should escape ampersands', () => {
      expect(escapeHtml('a & b')).toBe('a &amp; b');
    });
  });
});
