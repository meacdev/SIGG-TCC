import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Icon, Notice } from './components';
import './defenses.css';

async function download(path: string, name: string) {
  const result = await api.download(path);
  const url = URL.createObjectURL(result.body.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export interface Criterion {
  id_criterio: number;
  nome: string;
  descricao: string;
  peso: string;
  pontuacao_maxima: string;
}
export interface Defense {
  id_banca: number;
  aluno: string;
  titulo: string;
  curso: string;
  data_inicio: string;
  data_fim: string;
  local: string;
  situacao: string;
  resultado: string | null;
  pode_avaliar: boolean;
  avaliacao_iniciada: boolean;
  avaliador: string;
  criterios: Criterion[];
  avaliacao: {
    id_avaliacao: number;
    data_envio: string;
    nota_individual: string;
    parecer: string | null;
    notas: { id_criterio: number; nota: string }[];
  } | null;
  avaliacoes_enviadas: number;
  total_avaliadores: number;
  media_final: string | null;
  avaliadores: { nome: string; enviada: boolean; nota_individual: string | null }[];
}
export const dateTime = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Manaus',
  }).format(new Date(value));
export const gradeText = (value: string | number) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number(value),
  );
export const failure = (error: unknown) =>
  error instanceof Error ? error.message : 'Não foi possível concluir a operação.';

export function Defenses({ onSessionEnded }: { onSessionEnded: (message: string) => void }) {
  const [list, setList] = useState<Defense[]>([]);
  const [selected, setSelected] = useState<Defense | null>(null);
  const [etag, setEtag] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const manuscript = new URLSearchParams(window.location.hash.split('?')[1]).get('manuscrito');
  function downloadManuscript(id: number) {
    setMessage('');
    void download(`/bancas/${id}/manuscrito`, 'manuscrito.pdf').catch(handle);
  }

  function handle(error: unknown) {
    if (error instanceof ApiError && error.status === 401)
      onSessionEnded('Sua sessão expirou. Entre novamente.');
    else setMessage(failure(error));
  }
  async function load(id: number) {
    setLoading(true);
    setMessage('');
    try {
      const result = await api.request<Defense>(`/bancas/${id}`, {}, true);
      setSelected(result.body.data);
      setEtag(result.etag || '');
      return true;
    } catch (error) {
      handle(error);
      return false;
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .request<Defense[]>(`/bancas?page=${page}&per_page=20`, {}, true)
      .then((result) => {
        if (active) {
          setList(result.body.data);
          setPages(result.body.meta?.pages || 1);
        }
      })
      .catch((error) => {
        if (active) handle(error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [page]);
  return (
    <section className="defense-portal">
      <div className="page-intro">
        <span className="eyebrow">AVALIAÇÃO ACADÊMICA</span>
        <h2>{selected ? 'Avaliar defesa' : 'Minhas bancas'}</h2>
        <p>
          {selected
            ? 'Registre suas notas nos critérios definidos pela disciplina.'
            : 'Bancas em que você participa como examinador, com acesso vigente.'}
        </p>
      </div>
      {message && <Notice message={message} />}
      {manuscript && /^\d+$/.test(manuscript) && (
        <button className="secondary" onClick={() => downloadManuscript(Number(manuscript))}>
          Baixar manuscrito do convite
        </button>
      )}
      {loading && <p role="status">Carregando bancas…</p>}
      {!selected && !loading && (
        <>
          {!list.length && !message && (
            <div className="empty-state">
              <Icon name="book" size={32} />
              <h3>Nenhuma banca disponível</h3>
              <p>
                As bancas aparecerão aqui quando sua participação estiver confirmada e o acesso
                estiver vigente.
              </p>
            </div>
          )}
          <div className="defense-list">
            {list.map((item) => (
              <article className="defense-card" key={item.id_banca}>
                <span className="eyebrow">DEFESA · {item.curso}</span>
                <h3>{item.titulo}</h3>
                <p>{item.aluno}</p>
                <small>{dateTime(item.data_inicio)} · horário de Manaus</small>
                <button className="secondary" onClick={() => load(item.id_banca)}>
                  Abrir defesa <Icon name="arrow" size={16} />
                </button>
              </article>
            ))}
          </div>
          {pages > 1 && (
            <nav className="pager" aria-label="Páginas de bancas">
              <button className="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>
                Anterior
              </button>
              <span>
                Página {page} de {pages}
              </span>
              <button
                className="secondary"
                disabled={page === pages}
                onClick={() => setPage(page + 1)}
              >
                Próxima
              </button>
            </nav>
          )}
        </>
      )}
      {selected && (
        <>
          <button
            className="text-button"
            onClick={() => {
              setSelected(null);
              setMessage('');
            }}
          >
            Voltar às minhas bancas
          </button>
          <DefenseSummary defense={selected} />
          <button className="secondary" onClick={() => downloadManuscript(selected.id_banca)}>
            Baixar manuscrito
          </button>
          <EvaluationForm
            key={selected.id_banca}
            defense={selected}
            etag={etag}
            onSaved={(updated, version) => {
              setSelected(updated);
              setEtag(version);
            }}
            onReload={() => load(selected.id_banca)}
            onError={handle}
          />
        </>
      )}
    </section>
  );
}

export function DefenseSummary({ defense }: { defense: Defense }) {
  return (
    <div className="defense-summary">
      <h3>{defense.titulo}</h3>
      <dl>
        <div>
          <dt>Estudante</dt>
          <dd>{defense.aluno}</dd>
        </div>
        <div>
          <dt>Curso</dt>
          <dd>{defense.curso}</dd>
        </div>
        <div>
          <dt>Defesa</dt>
          <dd>{dateTime(defense.data_inicio)} · Manaus</dd>
        </div>
        <div>
          <dt>Local</dt>
          <dd>{defense.local}</dd>
        </div>
        <div>
          <dt>Avaliador conectado</dt>
          <dd>{defense.avaliador}</dd>
        </div>
      </dl>
    </div>
  );
}

function EvaluationForm({
  defense,
  etag,
  onSaved,
  onReload,
  onError,
}: {
  defense: Defense;
  etag: string;
  onSaved: (defense: Defense, etag: string) => void;
  onReload: () => Promise<boolean>;
  onError: (error: unknown) => void;
}) {
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [opinion, setOpinion] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const locked =
    !defense.pode_avaliar || !defense.avaliacao_iniciada || !!defense.avaliacao || busy;
  const actual = Object.fromEntries(
    defense.avaliacao?.notas.map((item) => [item.id_criterio, item.nota]) || [],
  );
  const numeric = (c: Criterion) => Number((notes[c.id_criterio] || '').replace(',', '.'));
  function gradeError(c: Criterion) {
    const raw = notes[c.id_criterio]?.trim();
    if (!raw) return 'Informe a nota deste critério.';
    if (!/^-?\d+(?:[.,]\d{1,2})?$/.test(raw)) return 'Use um número com até duas casas decimais.';
    if (numeric(c) < 0) return 'A nota deve ser igual ou maior que zero.';
    if (numeric(c) > Number(c.pontuacao_maxima)) {
      return `A pontuação máxima é ${gradeText(c.pontuacao_maxima)}.`;
    }
    return '';
  }
  const complete = defense.criterios.every((c) => !gradeError(c));
  const preview = complete
    ? (defense.criterios.reduce(
        (sum, c) => sum + (numeric(c) / Number(c.pontuacao_maxima)) * Number(c.peso),
        0,
      ) *
        10) /
      defense.criterios.reduce((sum, c) => sum + Number(c.peso), 0)
    : null;
  async function start() {
    setBusy(true);
    setMessage('');
    try {
      const result = await api.request<Defense>(
        `/bancas/${defense.id_banca}/avaliacao/inicio`,
        { method: 'POST', headers: { 'If-Match': etag } },
        true,
      );
      onSaved(result.body.data, result.etag || '');
    } catch (error) {
      handleWriteError(error);
    } finally {
      setBusy(false);
    }
  }

  function handleWriteError(error: unknown) {
    setMessage(failure(error));
    if (!(error instanceof ApiError)) return;
    setFieldErrors(error.fields);
    if ([0, 412, 428, 503].includes(error.status) || error.code === 'AVALIACAO_ENVIADA') {
      setConflict(true);
    }
    if (error.status === 401) onError(error);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (locked) return;
    if (!complete) {
      const invalid = defense.criterios.filter((criterion) => gradeError(criterion));
      setFieldErrors(
        Object.fromEntries(invalid.map((c) => [`notas.${c.id_criterio}`, gradeError(c)])),
      );
      setMessage('Preencha as notas de todos os critérios obrigatórios, respeitando os limites.');
      document.getElementById(`nota-${invalid[0].id_criterio}`)?.focus();
      return;
    }
    if (!confirm) {
      setMessage('Confirme a revisão das notas antes de enviar.');
      return;
    }
    setBusy(true);
    setMessage('');
    setFieldErrors({});
    try {
      const result = await api.request<Defense>(
        `/bancas/${defense.id_banca}/avaliacao`,
        {
          method: 'POST',
          headers: { 'If-Match': etag },
          body: JSON.stringify({
            parecer: opinion,
            notas: defense.criterios.map((c) => ({
              id_criterio: c.id_criterio,
              nota: (notes[c.id_criterio] || '').replace(',', '.'),
            })),
          }),
        },
        true,
      );
      onSaved(result.body.data, result.etag || '');
      setSuccess(true);
      setNotes({});
    } catch (error) {
      handleWriteError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      {success && <Notice success message="Avaliação registrada com sucesso!" />}
      {message && (
        <Notice message={message}>
          {conflict && (
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  if (await onReload()) {
                    setConflict(false);
                    setMessage('');
                  }
                } finally {
                  setBusy(false);
                }
              }}
            >
              Atualizar dados da banca
            </button>
          )}
        </Notice>
      )}
      {!defense.pode_avaliar && !defense.avaliacao && (
        <Notice message="O formulário de avaliação está disponível somente no dia da defesa, no horário de Manaus, enquanto a banca estiver aberta." />
      )}
      {defense.pode_avaliar && !defense.avaliacao_iniciada && (
        <button
          className="primary"
          type="button"
          disabled={busy || !etag || conflict}
          onClick={() => void start()}
        >
          {busy ? 'Abrindo ficha…' : 'Iniciar avaliação'}
        </button>
      )}
      <form onSubmit={submit} aria-label="Ficha de avaliação" noValidate aria-busy={busy}>
        <div className="section-heading">
          <span>01</span>
          <h3>Ficha de avaliação</h3>
        </div>
        <p className="academic-hint">
          A nota de cada item é normalizada pela pontuação máxima. Os pesos definem a participação
          na nota individual, de 0 a 10.
        </p>
        <div className="criteria-list">
          {defense.criterios.map((c) => (
            <div className="criterion-card" key={c.id_criterio}>
              <div>
                <label htmlFor={`nota-${c.id_criterio}`}>{c.nome}</label>
                <p id={`descricao-${c.id_criterio}`}>{c.descricao}</p>
                <small>
                  Peso {c.peso} · Pontuação máxima {gradeText(c.pontuacao_maxima)}
                </small>
              </div>
              <input
                id={`nota-${c.id_criterio}`}
                aria-describedby={`descricao-${c.id_criterio}${fieldErrors[`notas.${c.id_criterio}`] ? ` erro-nota-${c.id_criterio}` : ''}`}
                aria-invalid={Boolean(fieldErrors[`notas.${c.id_criterio}`])}
                aria-label={`Nota de ${c.nome}`}
                inputMode="decimal"
                required
                disabled={locked}
                value={defense.avaliacao ? actual[c.id_criterio] : notes[c.id_criterio] || ''}
                placeholder="0,00"
                onChange={(event) => {
                  setNotes({ ...notes, [c.id_criterio]: event.target.value });
                  setFieldErrors((previous) => ({ ...previous, [`notas.${c.id_criterio}`]: '' }));
                  setConfirm(false);
                }}
              />
              {fieldErrors[`notas.${c.id_criterio}`] && (
                <small id={`erro-nota-${c.id_criterio}`}>
                  {fieldErrors[`notas.${c.id_criterio}`]}
                </small>
              )}
            </div>
          ))}
        </div>
        <label className="field" htmlFor="evaluation-opinion">
          Parecer do avaliador (opcional)
          <textarea
            id="evaluation-opinion"
            rows={4}
            maxLength={4000}
            value={defense.avaliacao ? defense.avaliacao.parecer || '' : opinion}
            disabled={locked}
            onChange={(event) => {
              setOpinion(event.target.value);
              setConfirm(false);
            }}
          />
        </label>
        <div className="grade-result">
          <span>
            {defense.avaliacao ? 'Nota individual registrada' : 'Prévia da nota individual'}
          </span>
          <strong>
            {defense.avaliacao
              ? gradeText(defense.avaliacao.nota_individual)
              : preview === null
                ? '—'
                : gradeText(preview)}
            <small> / 10</small>
          </strong>
        </div>
        {defense.avaliacao ? (
          <p className="academic-hint">
            Enviada em {dateTime(defense.avaliacao.data_envio)}. As notas registradas não podem ser
            sobrescritas por este formulário.
          </p>
        ) : (
          <>
            <label className="confirmation-check">
              <input
                type="checkbox"
                checked={confirm}
                disabled={locked}
                onChange={(event) => setConfirm(event.target.checked)}
              />
              Revisei as notas e confirmo o envio definitivo da avaliação.
            </label>
            <button className="primary" disabled={locked || !etag || conflict}>
              {busy ? 'Enviando avaliação…' : 'Enviar avaliação'}
            </button>
          </>
        )}
      </form>
      <div className="section-heading">
        <span>02</span>
        <h3>Consolidação da banca</h3>
      </div>
      <p className="academic-hint">
        {defense.avaliacoes_enviadas} de {defense.total_avaliadores} avaliações enviadas.
      </p>
      <ul className="examiner-list">
        {defense.avaliadores.map((item, index) => (
          <li key={index}>
            <span>{item.nome}</span>
            <strong>
              {item.enviada ? `${gradeText(item.nota_individual!)} / 10` : 'Pendente'}
            </strong>
          </li>
        ))}
      </ul>
      <div className="grade-result">
        <span>Média final da banca</span>
        <strong>
          {defense.media_final === null
            ? 'Aguardando avaliações'
            : `${gradeText(defense.media_final)} / 10`}
        </strong>
      </div>
    </>
  );
}
