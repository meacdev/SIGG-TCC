import type { Course, Envelope, Tokens, User } from './types';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

// Credentials deliberately live only in memory. Reloading the page requires a new login.
export function createApi(base = import.meta.env.VITE_API_BASE_URL || '/api/v1') {
  let tokens: Tokens | null = null;
  let refreshing: Promise<void> | null = null;
  const clearSession = () => {
    tokens = null;
  };

  async function request<T>(
    path: string,
    init: RequestInit = {},
    protectedRoute = false,
    retry = true,
  ): Promise<{ body: Envelope<T>; etag: string | null }> {
    const headers = new Headers(init.headers);
    if (init.body) headers.set('Content-Type', 'application/json');
    if (protectedRoute && tokens) headers.set('Authorization', `Bearer ${tokens.access_token}`);
    let response: Response;
    try {
      response = await fetch(`${base.replace(/\/$/, '')}${path}`, {
        ...init,
        headers,
        cache: 'no-store',
      });
    } catch {
      throw new ApiError(
        0,
        'REDE_INDISPONIVEL',
        'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.',
      );
    }
    if (response.status === 204) return { body: { data: undefined as T }, etag: null };
    const payload = await response.json().catch(() => null);
    if (!payload)
      throw new ApiError(
        response.status,
        'RESPOSTA_INVALIDA',
        'O servidor está indisponível ou retornou uma resposta inválida. Tente novamente.',
      );
    if (!response.ok) {
      if (
        protectedRoute &&
        response.status === 401 &&
        payload.error?.code === 'TOKEN_EXPIRADO' &&
        tokens &&
        retry
      ) {
        refreshing ??= refresh().finally(() => {
          refreshing = null;
        });
        await refreshing;
        return request<T>(path, init, true, false);
      }
      if (
        protectedRoute &&
        response.status === 401 &&
        payload.error?.code !== 'CREDENCIAIS_INVALIDAS'
      )
        clearSession();
      const error = payload.error;
      let message = error?.message || 'Não foi possível concluir a operação. Tente novamente.';
      if (response.status === 429) {
        const seconds = Number(response.headers.get('Retry-After'));
        message =
          seconds > 0
            ? `Muitas tentativas. Aguarde ${Math.ceil(seconds)} segundos e tente novamente.`
            : 'Muitas tentativas. Aguarde alguns instantes e tente novamente.';
      }
      throw new ApiError(response.status, error?.code || 'ERRO_SERVIDOR', message, error?.fields);
    }
    return { body: payload, etag: response.headers.get('ETag') };
  }

  async function refresh() {
    if (!tokens) throw new ApiError(401, 'SESSAO_EXPIRADA', 'Sua sessão expirou. Entre novamente.');
    const previous = tokens;
    try {
      const result = await request<Tokens>('/auth/refresh', {
        method: 'POST',
        headers: { Authorization: `Bearer ${previous.refresh_token}` },
      });
      tokens = { ...previous, ...result.body.data };
    } catch (error) {
      clearSession();
      throw error;
    }
  }

  return {
    hasSession: () => tokens !== null,
    clearSession,
    signup: (data: object) =>
      request<User>('/usuarios', { method: 'POST', body: JSON.stringify(data) }),
    async courses(signal?: AbortSignal) {
      const courses: Course[] = [];
      let page = 1;
      let pages = 1;
      do {
        const result = await request<Course[]>(`/cursos?per_page=100&page=${page}`, { signal });
        courses.push(...result.body.data);
        pages = result.body.meta?.pages || 1;
        page++;
      } while (page <= pages);
      return courses;
    },
    async login(email_usuario: string, senha: string) {
      const result = await request<Tokens>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email_usuario, senha }),
      });
      tokens = result.body.data;
    },
    profile: () => request<User>('/usuarios/me', {}, true),
    update: (data: object, etag: string) =>
      request<User>(
        '/usuarios/me',
        { method: 'PATCH', headers: { 'If-Match': etag }, body: JSON.stringify(data) },
        true,
      ),
    async deactivate(senha_atual: string, etag: string) {
      await request<void>(
        '/usuarios/me',
        { method: 'DELETE', headers: { 'If-Match': etag }, body: JSON.stringify({ senha_atual }) },
        true,
      );
      clearSession();
    },
    async logout() {
      try {
        await request<void>('/auth/logout', { method: 'DELETE' }, true);
      } finally {
        clearSession();
      }
    },
  };
}

export const api = createApi();
