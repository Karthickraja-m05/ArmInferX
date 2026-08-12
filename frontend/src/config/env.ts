/**
 * Application environment configuration options.
 */
export const ENV = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || '',
  MODE: import.meta.env.MODE || 'development',
  IS_DEV: import.meta.env.DEV,
};
