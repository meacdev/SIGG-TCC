import { useEffect, useState } from 'react';
import { api, ApiError } from './api';
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

interface StudentRow {
  id_matricula: number;
  nome: string;
  matricula: string;
  id_etapa: number | null;
  total_atas: number;
  ultima_reuniao: string | null;
  ultima_entrega: string | null;
  ultima_atividade: string;
  dias_inatividade: number;
  inativo: boolean;
}
interface Matrix {
  data: StudentRow[];
  meta: { page: number; pages: number; total: number; total_turma: number; total_inativos: number };
  message?: string;
  mensagem_padrao: string;
}
interface Preview {
  id_lote: string;
  quantidade: number;
  mensagem: string;
  expira_em: string;
}
interface Result {
  id_lote: string;
  total: number;
  enviados: number;
  pendentes: number;
  cancelados: number;
}
interface Meeting {
  id_reuniao: number;
  data_encontro: string;
  resumo: string;
  orientador: string;
  autor: string;
  data_registro: string;
}
const day = (value: string | null) =>
  value ? value.split('-').reverse().join('/') : 'Nenhum registro';
const EMPTY = 'Selecione ao menos um estudante para efetuar o disparo do e-mail de alerta.';

export function Monitoring({ onSessionEnded }: SessionProps) {
  const [classes, setClasses] = useState<ClassItem[]>([]),
    [allowed, setAllowed] = useState<boolean | null>(null),
    [classId, setClassId] = useState(''),
    [status, setStatus] = useState('todos');
  const [matrix, setMatrix] = useState<Matrix | null>(null),
    [page, setPage] = useState(1),
    [attempt, setAttempt] = useState(0),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(''),
    [success, setSuccess] = useState(''),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [all, setAll] = useState(false),
    [excluded, setExcluded] = useState<Set<number>>(new Set());
  const [preview, setPreview] = useState<Preview | null>(null),
    [result, setResult] = useState<Result | null>(null),
    [failedBatch, setFailedBatch] = useState<string | null>(null);
  const [history, setHistory] = useState<StudentRow | null>(null),
    [records, setRecords] = useState<Meeting[]>([]),
    [historyPage, setHistoryPage] = useState(1),
    [historyPages, setHistoryPages] = useState(1),
    [historyBusy, setHistoryBusy] = useState(false),
    [historyError, setHistoryError] = useState('');
  function error(e: unknown) {
    setMessage(failure(e));
    sessionError(e, onSessionEnded);
  }
  function clearSelection() {
    setSelected(new Set());
    setAll(false);
    setExcluded(new Set());
  }
  useEffect(() => {
    let active = true;
    api
      .profile()
      .then(async (r) => {
        const user = r.body.data;
        const permitted =
          !!user.docente &&
          user.docente.tipo_docente === 'interno' &&
          user.perfis.some((p) => ['professor_disciplina', 'coordenador'].includes(p));
        if (!active) return;
        setAllowed(permitted);
        if (!permitted) {
          setMessage(
            'Você não possui permissão para acessar o monitoramento ou enviar alertas desta turma.',
          );
          return;
        }
        const items = await catalog<ClassItem>('/turmas?ativa_turma=true');
        if (active) setClasses(items);
      })
      .catch((e) => {
        if (active) error(e);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    if (!classId) return;
    setLoading(true);
    setMatrix(null);
    api
      .request<StudentRow[]>(
        `/turmas/${classId}/monitoramento?status=${status}&page=${page}&per_page=20`,
        {},
        true,
      )
      .then((r) => {
        if (active) {
          const data = r.body as Matrix;
          const lastPage = Math.max(1, data.meta.pages);
          if (page > lastPage) setPage(lastPage);
          else setMatrix(data);
        }
      })
      .catch((e) => {
        if (active) error(e);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [classId, status, page, attempt]);
  useEffect(() => {
    let active = true;
    if (!history || !classId) return;
    setHistoryBusy(true);
    setHistoryError('');
    api
      .request<Meeting[]>(
        `/turmas/${classId}/monitoramento/${history.id_matricula}/atas?page=${historyPage}&per_page=10`,
        {},
        true,
      )
      .then((r) => {
        if (active) {
          setRecords(r.body.data);
          setHistoryPages(r.body.meta?.pages || 1);
        }
      })
      .catch((e) => {
        if (active) {
          setHistoryError(failure(e));
          sessionError(e, onSessionEnded);
        }
      })
      .finally(() => {
        if (active) setHistoryBusy(false);
      });
    return () => {
      active = false;
    };
  }, [history, historyPage, classId]);
  const count = all
    ? Math.max(0, (matrix?.meta.total_inativos || 0) - excluded.size)
    : selected.size;
  function isChecked(row: StudentRow) {
    return row.inativo && (all ? !excluded.has(row.id_matricula) : selected.has(row.id_matricula));
  }
  function toggle(row: StudentRow) {
    if (all) {
      const next = new Set(excluded);
      if (next.has(row.id_matricula)) next.delete(row.id_matricula);
      else next.add(row.id_matricula);
      setExcluded(next);
    } else {
      const next = new Set(selected);
      if (next.has(row.id_matricula)) next.delete(row.id_matricula);
      else next.add(row.id_matricula);
      setSelected(next);
    }
  }
  async function prepare() {
    setMessage('');
    setSuccess('');
    if (!count) {
      setMessage(EMPTY);
      return;
    }
    setBusy(true);
    try {
      const r = await api.request<Preview>(
        `/turmas/${classId}/monitoramento/previa`,
        {
          method: 'POST',
          body: JSON.stringify(
            all
              ? { todos_inativos: true, ids_excluidas: [...excluded] }
              : { ids_matriculas: [...selected] },
          ),
        },
        true,
      );
      setPreview(r.body.data);
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function send(identifier: string) {
    setBusy(true);
    setMessage('');
    setSuccess('');
    try {
      const r = await api.request<Result>(
        `/turmas/${classId}/monitoramento/lotes/${identifier}/confirmar`,
        { method: 'POST', body: '{}' },
        true,
      );
      setResult(r.body.data);
      setPreview(null);
      if (r.body.code === 'UC_13_M05') {
        setMessage(r.body.message || 'Uma ou mais notificações ficaram pendentes.');
        setFailedBatch(identifier);
      } else {
        setSuccess(r.body.message || 'Lote processado.');
        setFailedBatch(null);
      }
      clearSelection();
      setAttempt(attempt + 1);
    } catch (e) {
      error(e);
      if (e instanceof ApiError && e.status === 409) {
        setPreview(null);
        clearSelection();
        setAttempt(attempt + 1);
      }
    } finally {
      setBusy(false);
    }
  }
  function changeClass(value: string) {
    setClassId(value);
    setPage(1);
    setMatrix(null);
    clearSelection();
    setMessage('');
    setSuccess('');
    setResult(null);
    setFailedBatch(null);
  }
  return (
    <section>
      <div className="page-intro">
        <span className="eyebrow">ACOMPANHAMENTO ACADÊMICO</span>
        <h2>Monitorar Prazos</h2>
        <p>
          Consulte a atividade da turma e envie cobranças aos estudantes com mais de 30 dias de
          inatividade.
        </p>
      </div>
      {message && <Notice message={message} />} {success && <Notice success message={success} />}
      {allowed === null && <p aria-live="polite">Verificando acesso…</p>}
      {allowed && (
        <>
          <div className="academic-grid">
            <div className="field">
              <label htmlFor="turma-monitoramento">Turma de TCC</label>
              <select
                id="turma-monitoramento"
                value={classId}
                disabled={busy}
                onChange={(e) => changeClass(e.target.value)}
              >
                <option value="">Selecione uma turma ativa</option>
                {classes.map((c) => (
                  <option key={c.id_turma} value={c.id_turma}>
                    {c.codigo_turma} · {c.periodo_letivo} · TCC {c.nivel_turma}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="status-monitoramento">Status</label>
              <select
                id="status-monitoramento"
                value={status}
                disabled={busy || !classId}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(1);
                  clearSelection();
                }}
              >
                <option value="todos">Todos os estudantes</option>
                <option value="inativos">Apenas Inativos (&gt; 30 dias)</option>
              </select>
            </div>
          </div>
          {!classes.length && (
            <p className="academic-empty">
              Nenhuma turma ativa disponível nos seus vínculos acadêmicos.
            </p>
          )}
          {classId && (
            <>
              <div className="academic-actions">
                <button
                  className="secondary"
                  disabled={busy || loading}
                  onClick={() => {
                    clearSelection();
                    setMessage('');
                    setAttempt(attempt + 1);
                  }}
                >
                  Atualizar matriz
                </button>
              </div>
              {loading && <p aria-live="polite">Consultando atividade da turma…</p>}
              {matrix && (
                <>
                  <p className="academic-hint">
                    {matrix.meta.total_turma} estudantes · {matrix.meta.total_inativos} com
                    inatividade superior a 30 dias. A contagem considera a última reunião ou entrega
                    registrada; sem atividade, considera a matrícula.
                  </p>
                  {matrix.message && <Notice success message={matrix.message} />}
                  <div className="academic-actions">
                    <button
                      className="secondary"
                      disabled={busy || !matrix.meta.total_inativos}
                      onClick={() => {
                        setAll(true);
                        setExcluded(new Set());
                        setSelected(new Set());
                      }}
                    >
                      Selecionar Todos em Atraso
                    </button>
                    <button
                      className="secondary"
                      disabled={busy || !count}
                      onClick={clearSelection}
                    >
                      Limpar seleção
                    </button>
                    <span aria-live="polite">
                      {count} selecionado(s){all ? ' em todas as páginas' : ''}
                    </span>
                  </div>
                  <p className="academic-hint">
                    Em telas estreitas, deslize a tabela horizontalmente para consultar todas as
                    colunas.
                  </p>
                  <div
                    className="academic-table-wrap monitoring-table"
                    tabIndex={0}
                    role="region"
                    aria-label="Matriz da turma"
                  >
                    <table className="academic-table">
                      <caption>Atividade dos estudantes da turma selecionada</caption>
                      <thead>
                        <tr>
                          <th scope="col">Selecionar</th>
                          <th scope="col">Estudante / Matrícula</th>
                          <th scope="col">Total de atas</th>
                          <th scope="col">Última reunião</th>
                          <th scope="col">Dias de inatividade</th>
                          <th scope="col">Situação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {matrix.data.map((row) => (
                          <tr key={row.id_matricula}>
                            <td>
                              <input
                                type="checkbox"
                                aria-label={`Selecionar ${row.nome}, matrícula ${row.matricula}`}
                                checked={isChecked(row)}
                                disabled={!row.inativo || busy}
                                onChange={() => toggle(row)}
                              />
                            </td>
                            <th scope="row">
                              <button
                                className="text-button"
                                onClick={() => {
                                  setHistory(row);
                                  setHistoryPage(1);
                                  setRecords([]);
                                }}
                              >
                                {row.nome}
                              </button>
                              <small className="monitoring-registration">{row.matricula}</small>
                            </th>
                            <td>
                              <button
                                className="text-button"
                                aria-label={`Ver ${row.total_atas} atas de ${row.nome}`}
                                onClick={() => {
                                  setHistory(row);
                                  setHistoryPage(1);
                                  setRecords([]);
                                }}
                              >
                                {row.total_atas}
                              </button>
                            </td>
                            <td>{day(row.ultima_reuniao)}</td>
                            <td>
                              {row.dias_inatividade}
                              <small className="monitoring-registration">
                                Última atividade: {day(row.ultima_atividade)}
                                {row.ultima_entrega ? ` · Entrega: ${day(row.ultima_entrega)}` : ''}
                              </small>
                            </td>
                            <td>
                              {row.inativo ? (
                                <span className="monitoring-overdue">Inativo &gt; 30 dias</span>
                              ) : (
                                <span className="monitoring-current">Em acompanhamento</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!matrix.data.length && !matrix.message && (
                    <p className="academic-empty">Nenhum estudante neste filtro ou página.</p>
                  )}
                  <Pager page={page} pages={matrix.meta.pages} onChange={setPage} />
                  <div className="academic-actions">
                    <button
                      className="primary"
                      disabled={busy || !matrix.meta.total_inativos}
                      onClick={prepare}
                    >
                      Disparar Notificação de Cobrança
                    </button>
                  </div>
                </>
              )}
              {result && (
                <p className="academic-hint" aria-live="polite">
                  Resultado do lote: {result.enviados} enviado(s), {result.pendentes} pendente(s),{' '}
                  {result.cancelados} cancelado(s).
                </p>
              )}
              {failedBatch && (
                <button className="secondary" disabled={busy} onClick={() => send(failedBatch)}>
                  Tentar novamente os pendentes
                </button>
              )}
            </>
          )}
        </>
      )}
      {preview && (
        <ConfirmDialog
          title="Confirmar cobrança por e-mail"
          onClose={() => !busy && setPreview(null)}
        >
          <p>{preview.quantidade} destinatário(s) selecionado(s).</p>
          <h3>Mensagem padrão de cobrança</h3>
          <p className="academic-summary">{preview.mensagem}</p>
          <p className="academic-hint">
            O e-mail também identifica o estudante e a turma. A situação é conferida novamente antes
            do envio.
          </p>
          {message && <Notice message={message} />}
          <div className="academic-actions">
            <button className="secondary" disabled={busy} onClick={() => setPreview(null)}>
              Cancelar
            </button>
            <button className="primary" disabled={busy} onClick={() => send(preview.id_lote)}>
              {busy ? 'Enviando…' : 'Enviar E-mails'}
            </button>
          </div>
        </ConfirmDialog>
      )}
      {history && (
        <ConfirmDialog
          title={`Histórico de atas — ${history.nome}`}
          onClose={() => setHistory(null)}
        >
          {historyBusy ? (
            <p aria-live="polite">Carregando histórico…</p>
          ) : historyError ? (
            <Notice message={historyError} />
          ) : (
            <>
              {!records.length && (
                <p className="academic-empty">
                  Nenhuma ata registrada para este estudante nesta turma.
                </p>
              )}
              {records.map((r) => (
                <article className="academic-box" key={r.id_reuniao}>
                  <h3>Encontro de {r.data_encontro}</h3>
                  <p className="academic-summary">{r.resumo}</p>
                  <p className="academic-hint">
                    Orientador: {r.orientador} · Registrado por {r.autor}
                  </p>
                </article>
              ))}
              <Pager page={historyPage} pages={historyPages} onChange={setHistoryPage} />
            </>
          )}
          <button className="secondary" onClick={() => setHistory(null)}>
            Fechar histórico
          </button>
        </ConfirmDialog>
      )}
    </section>
  );
}
