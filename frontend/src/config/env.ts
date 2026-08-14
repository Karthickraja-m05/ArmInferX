/**
 * Application environment configuration options.
 */
const rawApiUrl = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? 'https://armserve.onrender.com' : '')
).trim();

export const ENV = {
  API_BASE_URL: rawApiUrl.replace(/\/+$/, ''),
  MODE: import.meta.env.MODE || 'development',
  IS_DEV: import.meta.env.DEV,
};

