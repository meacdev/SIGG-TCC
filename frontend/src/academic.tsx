import { type InputHTMLAttributes, type ReactNode, useEffect, useRef } from 'react';
import { api, ApiError } from './api';

export type SessionProps = { onSessionEnded: (message: string) => void };
export const failure = (error: unknown) =>
  error instanceof Error ? error.message : 'Não foi possível concluir a operação.';
export function sessionError(error: unknown, end: SessionProps['onSessionEnded']) {
  if (error instanceof ApiError && error.status === 401)
    end('Sua sessão expirou. Entre novamente.');
}
export async function catalog<T>(path: string) {
  const items: T[] = [];
  let page = 1,
    pages = 1;
  do {
    const response = await api.request<T[]>(
      `${path}${path.includes('?') ? '&' : '?'}page=${page}&per_page=100`,
      {},
      true,
    );
    items.push(...response.body.data);
    pages = response.body.meta?.pages || 1;
    page++;
  } while (page <= pages);
  return items;
}
export function AcademicField({
  name,
  label,
  error,
  children,
}: {
  name: string;
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {children}
      {error && (
        <small className="field-error" id={`${name}-error`}>
          {error}
        </small>
      )}
    </div>
  );
}
export const fieldProps = (
  id: string,
  errors: Record<string, string>,
): InputHTMLAttributes<HTMLInputElement> => ({
  id,
  'aria-invalid': !!errors[id],
  'aria-describedby': errors[id] ? `${id}-error` : undefined,
});
export function Pager({
  page,
  pages,
  onChange,
}: {
  page: number;
  pages: number;
  onChange: (page: number) => void;
}) {
  return pages > 1 ? (
    <nav className="academic-pager" aria-label="Paginação">
      <button className="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Anterior
      </button>
      <span>
        Página {page} de {pages}
      </span>
      <button className="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Próxima
      </button>
    </nav>
  ) : null;
}
export function ConfirmDialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    return () => {
      ref.current?.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="confirm-dialog"
      aria-labelledby="confirmation-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <h2 id="confirmation-title">{title}</h2>
      {children}
    </dialog>
  );
}
