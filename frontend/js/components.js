/**
 * Shared UI components for LitFoundry.
 * 
 * Stateless, reusable render-function components:
 * - Loading state
 * - Empty state
 * - Error with retry
 * - Confirmation dialog
 */

import { h, ref } from '/frontend/vendor/vue.runtime.esm-browser.prod.js';

/**
 * Loading spinner component
 */
export function LoadingComponent(props = {}) {
  return h('div', { class: 'loading-container text-center py-8' }, [
    h('div', { class: 'inline-block' }, [
      h('div', { class: 'spinner w-8 h-8 border-4 border-gray-300 border-t-primary rounded-full animate-spin' }),
    ]),
    props.message && h('p', { class: 'mt-4 text-gray-600' }, props.message),
  ]);
}

/**
 * Empty state component
 */
export function EmptyComponent(props = {}) {
  return h('div', { class: 'empty-container text-center py-12' }, [
    h('svg', {
      class: 'mx-auto h-12 w-12 text-gray-400',
      fill: 'none',
      stroke: 'currentColor',
      viewBox: '0 0 24 24',
    }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4',
      }),
    ]),
    h('h3', { class: 'mt-2 text-lg font-medium text-gray-900' }, props.title || 'No results'),
    props.message && h('p', { class: 'mt-1 text-sm text-gray-500' }, props.message),
  ]);
}

/**
 * Error component with retry button
 */
export function ErrorComponent(props = {}) {
  return h('div', { class: 'error-container text-center py-12' }, [
    h('svg', {
      class: 'mx-auto h-12 w-12 text-red-400',
      fill: 'none',
      stroke: 'currentColor',
      viewBox: '0 0 24 24',
    }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M12 9v2m0 4v2m0-10a8 8 0 100 16 8 8 0 000-16z',
      }),
    ]),
    h('h3', { class: 'mt-2 text-lg font-medium text-gray-900' }, 'Error'),
    h('p', { class: 'mt-1 text-sm text-gray-500' }, props.message || 'An error occurred'),
    props.onRetry && h('button', {
      class: 'mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-dark',
      onClick: props.onRetry,
    }, 'Retry'),
  ]);
}

/**
 * Confirmation dialog component
 */
export function ConfirmDialogComponent(props = {}) {
  const { title, message, onConfirm, onCancel, isOpen } = props;

  if (!isOpen) return null;

  return h('div', { class: 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50' }, [
    h('div', { class: 'bg-white rounded-lg shadow-lg p-6 max-w-sm' }, [
      h('h2', { class: 'text-lg font-semibold text-gray-900' }, title),
      h('p', { class: 'mt-2 text-sm text-gray-600' }, message),
      h('div', { class: 'mt-4 flex gap-2 justify-end' }, [
        h('button', {
          class: 'px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md',
          onClick: onCancel,
        }, 'Cancel'),
        h('button', {
          class: 'px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md',
          onClick: onConfirm,
        }, 'Confirm'),
      ]),
    ]),
  ]);
}

/**
 * Badge component for status/tags
 */
export function BadgeComponent(props = {}) {
  const variants = {
    default: 'bg-gray-100 text-gray-900',
    primary: 'bg-blue-100 text-blue-900',
    success: 'bg-green-100 text-green-900',
    warning: 'bg-yellow-100 text-yellow-900',
    danger: 'bg-red-100 text-red-900',
  };

  const classes = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[props.variant] || variants.default}`;

  return h('span', { class: classes }, props.text);
}

/**
 * Button component
 */
export function ButtonComponent(props = {}) {
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-dark',
    secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const classes = `inline-flex items-center border border-transparent font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 ${variants[props.variant] || variants.primary} ${sizes[props.size] || sizes.md}`;

  return h('button', {
    class: classes,
    onClick: props.onClick,
    disabled: props.disabled,
  }, props.text);
}
