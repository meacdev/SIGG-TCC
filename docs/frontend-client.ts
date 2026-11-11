/** Minimal integration example for React/TypeScript. Keep credentials in memory. */
export type Perfil = "aluno" | "professor_disciplina" | "orientador" | "coordenador" | "avaliador";
export interface Usuario {
  id_usuario: number;
  nome_usuario: string;
  email_usuario: string;
  perfis: Perfil[];
}
export interface Tokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: "Bearer";
  usuario?: Usuario;
}
export interface CriarTurma {
  periodo_letivo: string;
  codigo_turma: string;
  nivel_turma: 1 | 2;
  id_curso: number;
  id_docente_responsavel: number;
}
export interface Turma extends CriarTurma {
  id_turma: number;
  ativa_turma: boolean;
  autoinscricao_ativa_turma: boolean;
  data_atualizacao_turma: string;
  data_expiracao_acesso_turma: string | null;
  codigo_acesso?: string; // Returned only on creation / rotation.
}
export interface Envelope<T> { data: T; code?: string; message?: string }
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string,
              public fields?: Record<string, string>) { super(message); }
}

export function createSiggClient(baseUrl: string) {
  let credentials: Tokens | null = null;
  let refreshing: Promise<void> | null = null;

  async function refresh(): Promise<void> {
    if (!credentials) throw new ApiError(401, "SESSAO_EXPIRADA", "Entre novamente.");
    const response = await fetch(`${baseUrl}/auth/refresh`, {
      method: "POST", headers: { Authorization: `Bearer ${credentials.refresh_token}` },
    });
    const body = await response.json();
    if (!response.ok) {
      credentials = null;
      throw new ApiError(response.status, body.error.code, body.error.message);
    }
    credentials = { ...credentials, ...body.data };
  }

  async function request<T>(path: string, init: RequestInit = {}, retry = true):
    Promise<{ body: Envelope<T>; etag: string | null }> {
    const headers = new Headers(init.headers);
    if (init.body) headers.set("Content-Type", "application/json");
    if (credentials) headers.set("Authorization", `Bearer ${credentials.access_token}`);
    const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
    if (response.status === 204) return { body: { data: undefined as T }, etag: null };
    const body = await response.json();
    if (!response.ok) {
      if (response.status === 401 && body.error.code === "TOKEN_EXPIRADO" && retry && credentials) {
        refreshing ??= refresh().finally(() => { refreshing = null; });
        await refreshing;
        return request<T>(path, init, false);
      }
      throw new ApiError(response.status, body.error.code, body.error.message, body.error.fields);
    }
    return { body, etag: response.headers.get("ETag") };
  }

  return {
    request,
    async login(email_usuario: string, senha: string) {
      const result = await request<Tokens>("/auth/login", {
        method: "POST", body: JSON.stringify({ email_usuario, senha }),
      }, false);
      credentials = result.body.data;
      return credentials.usuario!;
    },
    async logout() {
      try { await request<void>("/auth/logout", { method: "DELETE" }); }
      finally { credentials = null; }
    },
    createClass(data: CriarTurma) {
      return request<Turma>("/turmas", { method: "POST", body: JSON.stringify(data) });
    },
    updateClass(id: number, data: Partial<CriarTurma>, etag: string) {
      return request<Turma>(`/turmas/${id}`, {
        method: "PATCH", headers: { "If-Match": etag }, body: JSON.stringify(data),
      });
    },
  };
}

// const api = createSiggClient(`${import.meta.env.VITE_API_URL}/api/v1`);
// Render ApiError.fields beside inputs; 412 means reload the current record.
// Trigger requests from real user actions; do not keep idle sessions alive with timers.
