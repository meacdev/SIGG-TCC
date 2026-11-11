import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, createApi } from './api';

afterEach(() => vi.unstubAllGlobals());
const json = (body: unknown, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });

describe('integração HTTP', () => {
  it('preserva o ETag e envia If-Match na edição e inativação', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json({ data: { access_token: 'access', refresh_token: 'refresh' } }))
      .mockResolvedValueOnce(json({ data: { id_usuario: 7 } }, 200, { ETag: '"version-1"' }))
      .mockResolvedValueOnce(json({ data: {} }, 200, { ETag: '"version-2"' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetcher);
    const client = createApi('/api/v1');
    await client.login('a@example.com', 'senha');
    expect((await client.profile()).etag).toBe('"version-1"');
    await client.update({ nome_usuario: 'Outro nome' }, '"version-1"');
    const headers = fetcher.mock.calls[2][1].headers as Headers;
    expect(headers.get('If-Match')).toBe('"version-1"');
    expect(headers.get('Authorization')).toBe('Bearer access');
    await client.deactivate('senha', '"version-2"');
    expect(fetcher.mock.calls[3][1].headers.get('If-Match')).toBe('"version-2"');
    expect(client.hasSession()).toBe(false);
  });
  it('apresenta os erros de campo da API e o tempo para nova tentativa', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          json(
            {
              error: { code: 'UC_01_M04', message: 'Este endereço de e-mail já está cadastrado.' },
            },
            409,
          ),
        )
        .mockResolvedValueOnce(json({ error: { code: 'LIMITE' } }, 429, { 'Retry-After': '60' })),
    );
    const client = createApi();
    await expect(client.signup({})).rejects.toMatchObject({ status: 409, code: 'UC_01_M04' });
    await expect(client.signup({})).rejects.toThrow('Aguarde 60 segundos');
  });
  it('reúne todas as páginas de cursos e não inventa opções', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json({ data: [{ id_curso: 1 }], meta: { pages: 2 } }))
      .mockResolvedValueOnce(json({ data: [{ id_curso: 2 }], meta: { pages: 2 } }));
    vi.stubGlobal('fetch', fetcher);
    expect(await createApi().courses()).toEqual([{ id_curso: 1 }, { id_curso: 2 }]);
    expect(fetcher.mock.calls[1][0]).toContain('page=2');
  });
  it('renova tokens sob demanda e substitui os dois tokens em memória', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json({ data: { access_token: 'a1', refresh_token: 'r1' } }))
      .mockResolvedValueOnce(json({ error: { code: 'TOKEN_EXPIRADO' } }, 401))
      .mockResolvedValueOnce(json({ data: { access_token: 'a2', refresh_token: 'r2' } }))
      .mockResolvedValueOnce(json({ data: { id_usuario: 1 } }));
    vi.stubGlobal('fetch', fetcher);
    const client = createApi();
    await client.login('a@example.com', 'senha');
    await client.profile();
    expect(fetcher.mock.calls[2][1].headers.get('Authorization')).toBe('Bearer r1');
    expect(fetcher.mock.calls[3][1].headers.get('Authorization')).toBe('Bearer a2');
  });
  it('não confunde erro de rede com sucesso ou resposta HTML com JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockRejectedValueOnce(new TypeError('offline'))
        .mockResolvedValueOnce(new Response('<html>502</html>', { status: 502 })),
    );
    const client = createApi();
    await expect(client.signup({})).rejects.toMatchObject({ code: 'REDE_INDISPONIVEL' });
    await expect(client.signup({})).rejects.toBeInstanceOf(ApiError);
  });
});
