import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, ApiError } from './client';

describe('apiFetch error normalizer', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('normalizes 400 domain validation error with error, detail, and request_id', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ 'X-Request-ID': 'req-400-header' }),
      json: async () => ({
        error: 'invalid_domain',
        detail: 'Domain contains invalid characters',
        request_id: 'req-400-body',
      }),
    });

    try {
      await apiFetch('/investigations');
      expect.fail('Should have thrown ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(400);
      expect(apiErr.code).toBe('invalid_domain');
      expect(apiErr.message).toBe('Domain contains invalid characters');
      expect(apiErr.requestId).toBe('req-400-body');
      expect(apiErr.retryAfter).toBeNull();
    }
  });

  it('normalizes 401 auth error with code', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'X-Request-ID': 'req-401' }),
      json: async () => ({
        error: 'invalid_api_key',
      }),
    });

    try {
      await apiFetch('/investigations');
      expect.fail('Should have thrown ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(401);
      expect(apiErr.code).toBe('invalid_api_key');
      expect(apiErr.requestId).toBe('req-401');
    }
  });

  it('normalizes 404 error with detail', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: new Headers(),
      json: async () => ({
        detail: 'Investigation not found',
      }),
    });

    try {
      await apiFetch('/investigations/unknown-id');
      expect.fail('Should have thrown ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(404);
      expect(apiErr.code).toBeNull();
      expect(apiErr.message).toBe('Investigation not found');
    }
  });

  it('normalizes 429 rate limit error with error and retry_after', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({
        'Retry-After': '60',
        'X-Request-ID': 'req-429',
      }),
      json: async () => ({
        error: 'rate_limited',
        retry_after: 60,
      }),
    });

    try {
      await apiFetch('/investigations');
      expect.fail('Should have thrown ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(429);
      expect(apiErr.code).toBe('rate_limited');
      expect(apiErr.retryAfter).toBe(60);
      expect(apiErr.requestId).toBe('req-429');
    }
  });

  it('handles network failure by throwing ApiError with status 0', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    try {
      await apiFetch('/investigations');
      expect.fail('Should have thrown ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(0);
      expect(apiErr.code).toBe('network_error');
    }
  });
});
