import { vi } from 'vitest';

const API_PREFIX = '/api';

export function json(body, { status = 200, headers = {} } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

export function noContent() {
  return new Response(null, { status: 204 });
}

export function apiError(status, detail) {
  return json({ detail }, { status });
}

export function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function compileRoute(key) {
  const [method, pattern] = key.split(' ');
  const names = [];
  const source = pattern.replace(/:(\w+)/g, (_, name) => {
    names.push(name);
    return '([^/]+)';
  });

  return { method, names, regex: new RegExp(`^${source}$`) };
}

function findHandler(routes, method, path) {
  for (const [key, handler] of Object.entries(routes)) {
    const route = compileRoute(key);
    const match = route.method === method && path.match(route.regex);

    if (match) {
      const params = Object.fromEntries(
        route.names.map((name, index) => [name, match[index + 1]]),
      );
      return { handler, params };
    }
  }

  return null;
}

function abortError() {
  return new DOMException('The operation was aborted.', 'AbortError');
}

export function mockApi(routes = {}) {
  const requests = [];

  const fetchMock = vi.fn(async (input, init = {}) => {
    const url = new URL(input);
    const method = init.method ?? 'GET';
    const path = url.pathname.slice(API_PREFIX.length);
    const request = {
      method,
      path,
      query: Object.fromEntries(url.searchParams),
      body: init.body === undefined ? undefined : JSON.parse(init.body),
      init,
    };
    requests.push(request);

    if (init.signal?.aborted) throw abortError();

    const found = findHandler(routes, method, path);
    if (!found) {
      return apiError(501, `Unexpected request: ${method} ${path}`);
    }

    const response = await found.handler({ ...request, params: found.params });
    if (response instanceof Error) throw response;
    if (init.signal?.aborted) throw abortError();

    return response;
  });

  vi.stubGlobal('fetch', fetchMock);

  return {
    routes,
    requests,
    fetchMock,
    requestsTo(method, path) {
      return requests.filter(
        (request) => request.method === method && request.path === path,
      );
    },
  };
}
