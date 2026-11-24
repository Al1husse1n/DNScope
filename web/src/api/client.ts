export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly retryAfter: number | null;
  readonly requestId: string | null;

  constructor(
    status: number,
    code: string | null = null,
    retryAfter: number | null = null,
    requestId: string | null = null,
    message?: string,
  ) {
    super(message || code || (status === 0 ? 'Network error' : `HTTP error ${status}`));
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
    this.requestId = requestId;
  }
}

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
}

export async function apiFetch<T>(
  path: string,
  options?: {
    method?: string;
    apiKey?: string | null;
    body?: unknown;
    signal?: AbortSignal;
  },
): Promise<T> {
  const baseUrl = getApiBaseUrl().replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${baseUrl}${cleanPath}`;

  const headers: Record<string, string> = {};
  if (options?.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (options?.apiKey) {
    headers['X-API-Key'] = options.apiKey;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: options?.method || 'GET',
      headers,
      body: options?.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options?.signal,
    });
  } catch {
    throw new ApiError(0, 'network_error', null, null, 'Network error');
  }

  const requestIdHeader = response.headers.get('X-Request-ID') || null;
  const retryAfterHeader = response.headers.get('Retry-After');
  let retryAfterSeconds: number | null = null;
  if (retryAfterHeader) {
    const parsed = parseInt(retryAfterHeader, 10);
    if (!isNaN(parsed)) {
      retryAfterSeconds = parsed;
    }
  }

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    try {
      return (await response.json()) as T;
    } catch {
      return undefined as T;
    }
  }

  // Error normalization
  let jsonBody: Record<string, unknown> | null = null;
  try {
    jsonBody = (await response.json()) as Record<string, unknown>;
  } catch {
    jsonBody = null;
  }

  const status = response.status;
  const rawError = typeof jsonBody?.error === 'string' ? jsonBody.error : null;
  const rawDetail = typeof jsonBody?.detail === 'string' ? jsonBody.detail : null;
  const bodyRequestId = typeof jsonBody?.request_id === 'string' ? jsonBody.request_id : null;
  const requestId = bodyRequestId || requestIdHeader;

  // Rate limit (429)
  if (status === 429) {
    let retryVal = retryAfterSeconds;
    if (typeof jsonBody?.retry_after === 'number') {
      retryVal = jsonBody.retry_after;
    }
    throw new ApiError(
      429,
      rawError || 'rate_limited',
      retryVal,
      requestId,
      rawDetail || 'Rate limit reached',
    );
  }

  // Domain validation (400)
  if (status === 400 && rawError === 'invalid_domain') {
    throw new ApiError(400, 'invalid_domain', null, requestId, rawDetail || 'Invalid domain');
  }

  // Auth errors (401 / 403)
  if (status === 401 || status === 403) {
    throw new ApiError(
      status,
      rawError || (status === 401 ? 'unauthorized' : 'forbidden'),
      null,
      requestId,
      rawDetail || rawError || 'Authentication error',
    );
  }

  // 404
  if (status === 404) {
    throw new ApiError(404, rawError, null, requestId, rawDetail || 'Not found');
  }

  // 422 FastAPI validation error
  if (status === 422) {
    throw new ApiError(422, rawError, null, requestId, 'Validation error');
  }

  // 500 / other
  throw new ApiError(status, rawError, null, requestId, rawDetail || `HTTP error ${status}`);
}
