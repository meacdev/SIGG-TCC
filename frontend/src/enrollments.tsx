import { useEffect, useState, type FormEvent } from 'react';
import { api } from './api';
import { Notice } from './components';
import {
  catalog,
  ConfirmDialog,
  failure,
  Pager,
  sessionError,
  type SessionProps,
} from './academic';
import type { ClassItem } from './classes';

export interface Enrollment {
  id_matricula: number;
  id_turma: number;
  id_aluno: number;
  nome: string;
  matricula: string;
  codigo_turma: string;
  periodo_letivo: string;
  nivel_turma: number;
  turma_ativa: boolean;
  situacao: string;
  notificacao?: string;
}
interface Student {
  id_aluno: number;
  nome: string;
  matricula: string;
}
export function Enrollments({ onSessionEnded }: SessionProps) {
  const [own, setOwn] = useState<boolean | null>(null),
    [classes, setClasses] = useState<ClassItem[]>([]),
    [classId, setClassId] = useState('');
  const [rows, setRows] = useState<Enrollment[]>([]),
    [students, setStudents] = useState<Student[]>([]),
    [query, setQuery] = useState(''),
    [code, setCode] = useState('');
  const [message, setMessage] = useState(''),
    [success, setSuccess] = useState(''),
    [busy, setBusy] = useState(false),
    [attempt, setAttempt] = useState(0),
    [page, setPage] = useState(1),
    [pages, setPages] = useState(1);
  const [removal, setRemoval] = useState<Enrollment | null>(null),
    [etag, setEtag] = useState(''),
    [confirmation, setConfirmation] = useState(''),
    [reason, setReason] = useState('');
  function error(e: unknown) {
    setMessage(failure(e));
    sessionError(e, onSessionEnded);
  }
  useEffect(() => {
    let active = true;
    api
      .profile()
      .then(async (r) => {
        if (!active) return;
        const student = !!r.body.data.aluno;
        setOwn(student);
        if (!student) {
          const items = await catalog<ClassItem>('/turmas?ativa_turma=true');
          if (active) setClasses(items);
        }
      })
      .catch(error);
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    if (own === null || (!own && !classId)) return;
    setRows([]);
    api
      .request<Enrollment[]>(
        `${own ? '/minhas-matriculas' : `/turmas/${classId}/matriculas`}?page=${page}&per_page=20`,
        {},
        true,
      )
      .then((r) => {
        if (active) {
          setRows(r.body.data);
          setPages(r.body.meta?.pages || 1);
        }
      })
      .catch((e) => {
        if (active) error(e);
      });
    return () => {
      active = false;
    };
  }, [own, classId, page, attempt]);
  async function search(event: FormEvent) {
    event.preventDefault();
    setMessage('');
    setStudents([]);
    if (query.trim().length < 2) {
      setMessage('Informe pelo menos dois caracteres para buscar.');
      return;
    }
    setBusy(true);
    try {
      const items = await catalog<Student>(
        `/turmas/${classId}/estudantes?q=${encodeURIComponent(query.trim())}`,
      );
      setStudents(items);
      if (!items.length) setMessage('Cadastro de estudante não encontrado!');
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function add(id?: number) {
    if (busy) return;
    setBusy(true);
    setMessage('');
    setSuccess('');
    try {
      const r = await api.request<Enrollment>(
        own ? '/matriculas/autoinscricao' : `/turmas/${classId}/matriculas`,
        { method: 'POST', body: JSON.stringify(own ? { codigo_acesso: code } : { id_aluno: id }) },
        true,
      );
      setSuccess(r.body.message || 'Estudante matriculado com sucesso!');
      setAttempt(attempt + 1);
      setCode('');
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function prepareRemove(row: Enrollment) {
    setBusy(true);
    setMessage('');
    try {
      const r = await api.request<Enrollment>(`/matriculas/${row.id_matricula}`, {}, true);
      setEtag(r.etag || '');
      setRemoval(row);
      setConfirmation('');
      setReason('');
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function remove(event: FormEvent) {
    event.preventDefault();
    if (!removal || busy) return;
    setMessage('');
    setBusy(true);
    try {
      const r = await api.request<Enrollment>(
        `/turmas/${classId}/matriculas/${removal.id_matricula}`,
        {
          method: 'DELETE',
          headers: { 'If-Match': etag },
          body: JSON.stringify({ confirmacao: confirmation, motivo: reason }),
        },
        true,
      );
      setSuccess(
        `${r.body.message}${r.body.data.notificacao === 'enviada' ? ' Notificação enviada.' : ' A notificação ficou pendente para nova tentativa.'}`,
      );
      setRemoval(null);
      setAttempt(attempt + 1);
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <div className="page-intro">
        <span className="eyebrow">VÍNCULOS ACADÊMICOS</span>
        <h2>Matrículas</h2>
        <p>
          {own
            ? 'Entre em uma turma usando o código compartilhado pelo professor.'
            : 'Gerencie os estudantes das turmas sob sua responsabilidade.'}
        </p>
      </div>
      {message && <Notice message={message} />} {success && <Notice success message={success} />}
      {own === null ? (
        <p aria-live="polite">Carregando matrículas…</p>
      ) : own ? (
        <form
          className="academic-box"
          onSubmit={(e) => {
            e.preventDefault();
            void add();
          }}
        >
          <h3>Entrar em uma turma</h3>
          <div className="field">
            <label htmlFor="codigo-inscricao">Código de acesso da turma</label>
            <input
              id="codigo-inscricao"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={24}
              autoComplete="off"
              required
            />
          </div>
          <div className="academic-actions">
            <button className="primary" disabled={busy}>
              Confirmar inscrição
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="field">
            <label htmlFor="turma-matriculas">Turma para gerenciar matrículas</label>
            <select
              id="turma-matriculas"
              value={classId}
              onChange={(e) => {
                setClassId(e.target.value);
                setPage(1);
                setStudents([]);
                setMessage('');
                setSuccess('');
              }}
            >
              <option value="">Selecione uma turma</option>
              {classes.map((c) => (
                <option key={c.id_turma} value={c.id_turma}>
                  {c.codigo_turma} · {c.periodo_letivo} · TCC {c.nivel_turma}
                </option>
              ))}
            </select>
          </div>
          {classId && (
            <form className="academic-box" onSubmit={search}>
              <h3>Adicionar estudante</h3>
              <div className="field">
                <label htmlFor="busca-estudante">Buscar por nome, matrícula ou e-mail</label>
                <input
                  id="busca-estudante"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  maxLength={100}
                  required
                  minLength={2}
                />
              </div>
              <div className="academic-actions">
                <button className="secondary" disabled={busy}>
                  Buscar estudante
                </button>
              </div>
              {students.map((s) => (
                <article key={s.id_aluno} className="academic-box">
                  <h4>{s.nome}</h4>
                  <p>Matrícula: {s.matricula}</p>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() => add(s.id_aluno)}
                  >
                    Matricular {s.nome}
                  </button>
                </article>
              ))}
            </form>
          )}
          {classId && (
            <p className="academic-hint">
              O código de acesso é gerado e copiado em <a href="#/turmas">Turmas</a>. Apenas contas
              ativas do curso podem ser incluídas.
            </p>
          )}
        </>
      )}
      {(own || classId) && (
        <>
          <h3>{own ? 'Minhas turmas' : 'Estudantes matriculados'}</h3>
          {!rows.length && <p className="academic-empty">Nenhuma matrícula ativa encontrada.</p>}
          <div className="academic-list">
            {rows.map((row) => (
              <article className="academic-box" key={row.id_matricula}>
                <h3>{own ? row.codigo_turma : row.nome}</h3>
                <p className="academic-meta">
                  {row.periodo_letivo} · TCC {row.nivel_turma} · Matrícula {row.matricula}
                  {!row.turma_ativa ? ' · Turma inativa' : ''}
                </p>
                {!own && (
                  <button className="secondary" disabled={busy} onClick={() => prepareRemove(row)}>
                    Remover {row.nome}
                  </button>
                )}
              </article>
            ))}
          </div>
          <Pager page={page} pages={pages} onChange={setPage} />
        </>
      )}
      {removal && (
        <ConfirmDialog
          title="Deseja realmente remover esse estudante?"
          onClose={() => !busy && setRemoval(null)}
        >
          <form onSubmit={remove}>
            <p>
              Para confirmar, digite{' '}
              <strong>
                {removal.nome}/{removal.codigo_turma}
              </strong>
              . O histórico será preservado.
            </p>
            {message && <Notice message={message} />}
            <div className="field">
              <label htmlFor="confirmacao-matricula">Confirmação da remoção</label>
              <input
                id="confirmacao-matricula"
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="motivo-matricula">Motivo da remoção</label>
              <textarea
                id="motivo-matricula"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                maxLength={2000}
              />
            </div>
            <div className="academic-actions">
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => setRemoval(null)}
              >
                Cancelar
              </button>
              <button
                className="primary"
                disabled={
                  busy ||
                  confirmation !== `${removal.nome}/${removal.codigo_turma}` ||
                  !reason.trim()
                }
              >
                Confirmar remoção
              </button>
            </div>
          </form>
        </ConfirmDialog>
      )}
    </section>
  );
}
