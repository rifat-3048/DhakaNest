const configuredApiUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL;

if (configuredApiUrl) {
  const parsed = new URL(configuredApiUrl);
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('NEXT_PUBLIC_API_BASE_URL must be an HTTP(S) URL.');
  }
}

if (process.env.NODE_ENV === 'production' && !configuredApiUrl) {
  throw new Error('NEXT_PUBLIC_API_BASE_URL is required for production builds.');
}

export const API_BASE_URL = (
  configuredApiUrl ?? 'http://127.0.0.1:8000'
).replace(/\/$/, '');
