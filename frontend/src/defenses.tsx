import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Icon, Notice } from './components';
import './defenses.css';
import { download, DocumentsPanel } from './documents';
import { conceptBand, decimal, type Concept, type Descriptors } from './official-rubric';

export interface Criterion {
  id_criterio: number;
  nome: string;
  componente: string | null;
  descricao: string;
  descritores: Descriptors | null;
  peso: string;
  pontuacao_maxima: string;
}
type ConceptKey = Concept['chave'];
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
  nivel?: number;
  tempo_apresentacao?: number | null;
  aprovacao_minima?: string;
  conceitos?: Concept[];
  componentes?: { chave: string; nome: string; pontos: string }[];
  criterios: Criterion[];
  avaliacao: {
    id_avaliacao: number;
    data_envio: string;
    nota_individual: string;
    subtotais?: Record<string, string>;
    parecer: string | null;
    notas: {
      id_criterio: number;
      conceito: ConceptKey | null;
      nota: string;
      nota_ponderada: string;
    }[];
  } | null;
  avaliacoes_enviadas: number;
  total_avaliadores: number;
  media_final: string | null;
  avaliadores: {
    nome: string;
    papel?: string;
    enviada: boolean;
    nota_individual: string | null;
  }[];
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
            ? 'Marque o conceito e registre a nota de cada critério da rubrica oficial.'
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
          <DocumentsPanel defense={selected} onVersion={setEtag} onError={handle} />
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
        {defense.tempo_apresentacao && (
          <div>
            <dt>Tempo de apresentação</dt>
            <dd>
              {defense.tempo_apresentacao} min (TCC {defense.nivel})
            </dd>
          </div>
        )}
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
  const [concepts, setConcepts] = useState<Record<number, ConceptKey>>({});
  const [opinion, setOpinion] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const locked =
    !defense.pode_avaliar || !defense.avaliacao_iniciada || !!defense.avaliacao || busy;
  const bands = defense.conceitos || [];
  const registered = Object.fromEntries(
    defense.avaliacao?.notas.map((item) => [item.id_criterio, item]) || [],
  );
  const totalWeight = defense.criterios.reduce((sum, c) => sum + Number(c.peso), 0) || 1;
  const numeric = (c: Criterion) => Number((notes[c.id_criterio] || '').replace(',', '.'));
  // Upper bound of a lower band is exclusive (7,9 means "below 8,0"), as in the official sheet.
  const conceptOf = (grade: number): ConceptKey | undefined =>
    [...bands]
      .sort((a, b) => Number(b.minimo) - Number(a.minimo))
      .find((band) => grade >= Number(band.minimo))?.chave;
  function gradeError(c: Criterion) {
    const concept = concepts[c.id_criterio];
    if (!concept) return 'Marque o conceito deste critério.';
    const raw = notes[c.id_criterio]?.trim();
    if (!raw) return 'Informe a nota deste critério.';
    if (!/^-?\d+(?:[.,]\d{1,2})?$/.test(raw)) return 'Use um número com até duas casas decimais.';
    if (numeric(c) < 0) return 'A nota deve ser igual ou maior que zero.';
    if (numeric(c) > Number(c.pontuacao_maxima)) {
      return `A pontuação máxima é ${gradeText(c.pontuacao_maxima)}.`;
    }
    const band = bands.find((item) => item.chave === concept);
    if (band && conceptOf(numeric(c)) !== concept) {
      return `A nota dada não pertence ao conceito marcado (${conceptBand(band)}).`;
    }
    return '';
  }
  const share = (c: Criterion, grade: number) =>
    ((grade / Number(c.pontuacao_maxima)) * Number(c.peso) * 10) / totalWeight;
  const complete = defense.criterios.every((c) => !gradeError(c));
  const preview = complete
    ? defense.criterios.reduce((sum, c) => sum + share(c, numeric(c)), 0)
    : null;
  const groups = (
    defense.componentes?.length
      ? defense.componentes
      : [{ chave: '', nome: 'Critérios', pontos: '10' }]
  )
    .map((component) => ({
      ...component,
      criterios: defense.criterios.filter(
        (c) => (c.componente || '') === component.chave || !defense.componentes?.length,
      ),
    }))
    .filter((component) => component.criterios.length);
  function subtotal(key: string) {
    if (defense.avaliacao?.subtotais?.[key]) return gradeText(defense.avaliacao.subtotais[key]);
    const items = defense.criterios.filter((c) => (c.componente || '') === key);
    if (items.some((c) => gradeError(c))) return '—';
    return gradeText(items.reduce((sum, c) => sum + share(c, numeric(c)), 0));
  }
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
      setMessage(
        'Marque o conceito e preencha a nota de todos os critérios, dentro da faixa do conceito.',
      );
      document
        .getElementById(
          concepts[invalid[0].id_criterio]
            ? `nota-${invalid[0].id_criterio}`
            : `conceito-${invalid[0].id_criterio}-${bands[0]?.chave}`,
        )
        ?.focus();
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
              conceito: concepts[c.id_criterio],
              nota: (notes[c.id_criterio] || '').replace(',', '.'),
            })),
          }),
        },
        true,
      );
      onSaved(result.body.data, result.etag || '');
      setSuccess(true);
      setNotes({});
      setConcepts({});
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
          Rubrica oficial da disciplina. Em cada critério, marque o conceito que se aplica e informe
          a nota dentro da faixa: {bands.map((band) => conceptBand(band)).join('; ')}. Nota
          ponderada = nota × peso ÷ 10; a nota individual é a soma das ponderadas, de 0 a 10.
        </p>
        {groups.map((component) => (
          <fieldset className="rubric-component" key={component.chave || 'criterios'}>
            <legend>
              {component.nome}
              {component.chave && ` (${decimal(component.pontos)} pontos)`}
            </legend>
            <div className="criteria-list">
              {component.criterios.map((c) => {
                const saved = registered[c.id_criterio];
                // Show band mismatches as soon as both the concept and the grade are filled in.
                const error =
                  fieldErrors[`notas.${c.id_criterio}`] ||
                  (!saved && concepts[c.id_criterio] && notes[c.id_criterio]?.trim()
                    ? gradeError(c)
                    : '');
                const chosen = saved ? saved.conceito : concepts[c.id_criterio];
                return (
                  <div className="criterion-card rubric-criterion" key={c.id_criterio}>
                    <div>
                      <strong id={`criterio-${c.id_criterio}`}>{c.nome}</strong>
                      {c.descricao && <p id={`descricao-${c.id_criterio}`}>{c.descricao}</p>}
                      <small>Peso {decimal(c.peso)}</small>
                    </div>
                    <div
                      className="concept-options"
                      role="radiogroup"
                      aria-labelledby={`criterio-${c.id_criterio}`}
                    >
                      {bands.map((band) => (
                        <label
                          key={band.chave}
                          className={
                            chosen === band.chave ? 'concept-option chosen' : 'concept-option'
                          }
                          htmlFor={`conceito-${c.id_criterio}-${band.chave}`}
                        >
                          <span>
                            <input
                              type="radio"
                              id={`conceito-${c.id_criterio}-${band.chave}`}
                              name={`conceito-${c.id_criterio}`}
                              value={band.chave}
                              aria-label={`${band.nome} (${decimal(band.minimo)} a ${decimal(band.maximo)})`}
                              checked={chosen === band.chave}
                              disabled={locked}
                              onChange={() => {
                                setConcepts({ ...concepts, [c.id_criterio]: band.chave });
                                setFieldErrors((previous) => ({
                                  ...previous,
                                  [`notas.${c.id_criterio}`]: '',
                                }));
                                setConfirm(false);
                              }}
                            />
                            <strong>{band.nome}</strong>
                            <small>
                              {decimal(band.minimo)} a {decimal(band.maximo)}
                            </small>
                          </span>
                          {c.descritores && <p>{c.descritores[band.chave]}</p>}
                        </label>
                      ))}
                    </div>
                    <label className="field" htmlFor={`nota-${c.id_criterio}`}>
                      Nota para o critério
                      <input
                        id={`nota-${c.id_criterio}`}
                        aria-describedby={error ? `erro-nota-${c.id_criterio}` : undefined}
                        aria-invalid={Boolean(error)}
                        inputMode="decimal"
                        required
                        disabled={locked}
                        value={saved ? saved.nota : notes[c.id_criterio] || ''}
                        placeholder="0,00"
                        onChange={(event) => {
                          setNotes({ ...notes, [c.id_criterio]: event.target.value });
                          setFieldErrors((previous) => ({
                            ...previous,
                            [`notas.${c.id_criterio}`]: '',
                          }));
                          setConfirm(false);
                        }}
                      />
                    </label>
                    <small>
                      Nota ponderada:{' '}
                      {saved
                        ? gradeText(saved.nota_ponderada)
                        : gradeError(c)
                          ? '—'
                          : gradeText(share(c, numeric(c)))}
                    </small>
                    {error && <small id={`erro-nota-${c.id_criterio}`}>{error}</small>}
                  </div>
                );
              })}
            </div>
            {component.chave && (
              <p className="academic-hint">
                Subtotal {component.nome}: {subtotal(component.chave)} / {decimal(component.pontos)}
              </p>
            )}
          </fieldset>
        ))}
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
            <span>
              {item.nome}
              {item.papel === 'presidente' && ' (orientador)'}
            </span>
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
