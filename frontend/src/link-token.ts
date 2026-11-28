/**
 * Links do e-mail chegam como `#/pagina?token=...` (UC14). O token fica só em memória e sai do
 * endereço assim que a página abre, para não ficar no histórico nem ser copiado junto do link.
 */
const captured = new Map<string, string>();

export function linkToken(page: string, location: Pick<Location, 'hash'> = window.location) {
  const [route, query = ''] = location.hash.replace(/^#\/?/, '').split('?');
  const token = new URLSearchParams(query).get('token');
  if (route === page && token) {
    captured.set(page, token);
    window.history.replaceState(null, '', `#/${page}`);
  }
  return captured.get(page) || '';
}

export function forgetLinkToken(page: string) {
  captured.delete(page);
}
