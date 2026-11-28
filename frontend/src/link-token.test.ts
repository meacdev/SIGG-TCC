import { afterEach, describe, expect, it, vi } from 'vitest';
import { forgetLinkToken, linkToken } from './link-token';

describe('token dos links do UC14', () => {
  afterEach(() => forgetLinkToken('aceitar-convite'));

  it('guarda o token e o remove do endereço', () => {
    const replaceState = vi.fn();
    vi.stubGlobal('window', { history: { replaceState } });
    expect(linkToken('aceitar-convite', { hash: '#/aceitar-convite?token=abc_123' })).toBe(
      'abc_123',
    );
    expect(replaceState).toHaveBeenCalledWith(null, '', '#/aceitar-convite');
    // Uma segunda leitura (StrictMode, nova renderização) continua com o mesmo token.
    expect(linkToken('aceitar-convite', { hash: '#/aceitar-convite' })).toBe('abc_123');
  });

  it('ignora o token de outra página', () => {
    vi.stubGlobal('window', { history: { replaceState: vi.fn() } });
    expect(linkToken('aceitar-convite', { hash: '#/confirmar-email?token=xyz' })).toBe('');
  });
});
