/**
 * Axios-based API client for LitFoundry.
 * 
 * Features:
 * - Same-origin requests only
 * - Automatic CSRF header attachment
 * - Typed error handling
 * - Session refresh on 401 (one retry)
 * - Request tracking
 */

/**
 * API Error class
 */
export class ApiError extends Error {
  constructor(code, message, status, requestId, details = {}) {
    super(message);
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
    this.name = 'ApiError';
  }
}

/**
 * API client class using Axios
 */
export class ApiClient {
  constructor() {
    this.baseURL = '/api/v1';
    this.csrfToken = this.getCSRFToken();
    this.instance = window.axios.create({
      baseURL: this.baseURL,
      withCredentials: true,
    });

    this.setupInterceptors();
  }

  /**
   * Get CSRF token from DOM (set by server)
   */
  getCSRFToken() {
    // Look for meta tag or cookie
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    // Look in cookies
    const cookies = document.cookie.split('; ');
    for (const cookie of cookies) {
      const [name, value] = cookie.split('=');
      if (name === 'csrf_token') return decodeURIComponent(value);
    }

    return null;
  }

  /**
   * Setup Axios interceptors
   */
  setupInterceptors() {
    // Request interceptor: add CSRF token
    this.instance.interceptors.request.use((config) => {
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method.toUpperCase())) {
        if (this.csrfToken) {
          config.headers['X-CSRF-TOKEN'] = this.csrfToken;
        }
      }
      return config;
    });

    // Response interceptor: handle errors and session refresh
    this.instance.interceptors.response.use(
      (response) => response,
      async (error) => {
        // Handle 401 (Unauthorized) with one refresh attempt
        if (error.response?.status === 401 && !error.config._retried) {
          error.config._retried = true;

          try {
            // Attempt to refresh session
            await this.instance.post('/auth/refresh');

            // Retry original request
            return this.instance(error.config);
          } catch (refreshError) {
            // Refresh failed, redirect to sign-in
            window.location.href = '/sign-in';
            throw this.parseError(refreshError);
          }
        }

        throw this.parseError(error);
      }
    );
  }

  /**
   * Parse error response into ApiError
   */
  parseError(error) {
    if (error.response?.data) {
      const { code, message, request_id, details } = error.response.data;
      return new ApiError(
        code || 'UNKNOWN_ERROR',
        message || 'An error occurred',
        error.response.status,
        request_id,
        details
      );
    }

    return new ApiError(
      'NETWORK_ERROR',
      error.message || 'Network error',
      0,
      null
    );
  }

  /**
   * GET request
   */
  async get(path, config = {}) {
    try {
      const response = await this.instance.get(path, config);
      return response.data;
    } catch (error) {
      throw this.parseError(error);
    }
  }

  /**
   * POST request
   */
  async post(path, data = {}, config = {}) {
    try {
      const response = await this.instance.post(path, data, config);
      return response.data;
    } catch (error) {
      throw this.parseError(error);
    }
  }

  /**
   * PUT request
   */
  async put(path, data = {}, config = {}) {
    try {
      const response = await this.instance.put(path, data, config);
      return response.data;
    } catch (error) {
      throw this.parseError(error);
    }
  }

  /**
   * PATCH request
   */
  async patch(path, data = {}, config = {}) {
    try {
      const response = await this.instance.patch(path, data, config);
      return response.data;
    } catch (error) {
      throw this.parseError(error);
    }
  }

  /**
   * DELETE request
   */
  async delete(path, config = {}) {
    try {
      const response = await this.instance.delete(path, config);
      return response.data;
    } catch (error) {
      throw this.parseError(error);
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
