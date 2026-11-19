import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Notice } from './components';
import './defenses.css';

const failure = (error: unknown) =>
  error instanceof Error ? error.message : 'Não foi possível concluir a operação.';

type ClassOption = { id_turma: number; codigo_turma: string; periodo_letivo: string };
type Criterion = { nome: string; descricao: string; peso: string };
type Rubric = {
  id: number;
  nome: string;
  situacao: string;
  versao: number;
  bloqueada: boolean;
  criterios: Criterion[];
};
type PriorRubric = Pick<Rubric, 'id' | 'nome' | 'versao'> & { periodo: string };
const blankCriterion = (): Criterion => ({ nome: '', descricao: '', peso: '' });
export function DefenseManagement({
  onSessionEnded,
}: {
  onSessionEnded: (message: string) => void;
}) {
  const [classes, setClasses] = useState<ClassOption[]>([]);
  const [classId, setClassId] = useState('');
  const [sourceId, setSourceId] = useState('');
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [source, setSource] = useState<PriorRubric[]>([]);
  const [rubricId, setRubricId] = useState<number>();
  const [name, setName] = useState('');
  const [criteria, setCriteria] = useState([blankCriterion()]);
  const [status, setStatus] = useState('rascunho');
  const [replace, setReplace] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const prefix = `/turmas/${classId}`;
  const sum =
    criteria.reduce((total, item) => total + Math.round(Number(item.peso || 0) * 1000), 0) / 1000;
  const currentRubric = rubrics.find((rubric) => rubric.id === rubricId);
  const activeRubric = rubrics.find((rubric) => rubric.situacao === 'ativa');
  const replacing = status === 'ativa' && activeRubric && activeRubric.id !== rubricId;

  function handleError(cause: unknown) {
    if (cause instanceof ApiError && cause.status === 401) onSessionEnded(cause.message);
    else setError(failure(cause));
  }

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      const items: ClassOption[] = [];
      let page = 1;
      while (true) {
        const { body } = await api.request<ClassOption[]>(
          `/turmas?page=${page}&per_page=100`,
          { signal: controller.signal },
          true,
        );
        items.push(...body.data);
        if (!body.meta?.pages || page >= Number(body.meta.pages)) break;
        page++;
      }
      if (!controller.signal.aborted) {
        setClasses(items);
        setClassId((value) => value || String(items[0]?.id_turma ?? ''));
      }
    })().catch((cause) => {
      if (!controller.signal.aborted) handleError(cause);
    });
    return () => controller.abort();
  }, []);

  async function load(signal?: AbortSignal) {
    if (!classId) return;
    const { body } = await api.request<Rubric[]>(`${prefix}/rubricas`, { signal }, true);
    if (!signal?.aborted) setRubrics(body.data);
  }

  useEffect(() => {
    if (!classId) return;
    const controller = new AbortController();
    setLoading(true);
    load(controller.signal)
      .catch((cause) => {
        if (!controller.signal.aborted) handleError(cause);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [classId]);

  useEffect(() => {
    if (!classId) return;
    const controller = new AbortController();
    api
      .request<PriorRubric[]>(`${prefix}/rubricas/anteriores`, { signal: controller.signal }, true)
      .then(({ body }) => {
        if (!controller.signal.aborted) setSource(body.data);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) handleError(cause);
      });
    return () => controller.abort();
  }, [classId]);

  async function importRubric() {
    setBusy(true);
    setMessage('');
    setError('');
    try {
      await api.request(
        `${prefix}/rubricas/importacoes`,
        { method: 'POST', body: JSON.stringify({ origem: Number(sourceId) }) },
        true,
      );
      setSourceId('');
      setMessage('Rubrica importada como rascunho. Você pode editá-la na lista da turma.');
      await load();
    } catch (cause) {
      handleError(cause);
    } finally {
      setBusy(false);
    }
  }

  function resetRubric() {
    setRubricId(undefined);
    setName('');
    setCriteria([blankCriterion()]);
    setStatus('rascunho');
    setReplace(false);
  }

  function editRubric(item: Rubric, copy = false) {
    setRubricId(copy ? undefined : item.id);
    setName(item.nome);
    setCriteria(
      item.criterios.map((criterion) => ({ ...criterion, peso: String(Number(criterion.peso)) })),
    );
    setStatus(copy ? 'rascunho' : item.situacao);
    setReplace(false);
    setMessage(copy ? 'Critérios copiados para o formulário. Salve para criar o rascunho.' : '');
    setError('');
  }

  async function saveRubric(event: FormEvent) {
    event.preventDefault();
    setError('');
    setMessage('');
    if (status === 'ativa' && sum !== 100 && sum !== 10) {
      setError('Para ativar a rubrica, ajuste a soma dos pesos para 100 ou 10.');
      return;
    }
    setBusy(true);
    try {
      await api.request(
        `${prefix}/rubricas${rubricId ? `/${rubricId}` : ''}`,
        {
          method: rubricId ? 'PATCH' : 'POST',
          body: JSON.stringify({
            nome: name,
            situacao: status,
            criterios: criteria,
            substituir: replacing && replace ? activeRubric.id : undefined,
          }),
        },
        true,
      );
      resetRubric();
      setMessage('Rubrica salva.');
      await load();
    } catch (cause) {
      handleError(cause);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="defense-portal defense-management">
      <div className="academic-box">
        <h2>Rubricas de avaliação</h2>
        <p>Prepare os critérios e os pesos das avaliações da turma.</p>
        <label className="field" htmlFor="def-class">
          Turma
          <select
            id="def-class"
            value={classId}
            disabled={busy}
            onChange={(e) => {
              setClassId(e.target.value);
              setRubrics([]);
              setSource([]);
              setSourceId('');
              resetRubric();
              setMessage('');
              setError('');
            }}
          >
            <option value="">Selecione uma turma</option>
            {classes.map((item) => (
              <option key={item.id_turma} value={item.id_turma}>
                {item.codigo_turma}
              </option>
            ))}
          </select>
        </label>
        {(loading || busy) && <p role="status">{busy ? 'Salvando…' : 'Carregando a turma…'}</p>}
        {error && <Notice message={error} />}
        {message && <Notice success message={message} />}
        {classId && !loading && (
          <>
            <h3>Rubricas da turma</h3>
            {!rubrics.length && <p>Nenhuma rubrica cadastrada.</p>}
            <ul className="defense-records">
              {rubrics.map((rubric) => (
                <li key={rubric.id}>
                  <strong>{rubric.nome}</strong> · v{rubric.versao} · {rubric.situacao}
                  {rubric.bloqueada && ' · bloqueada após avaliação'}
                  <button type="button" disabled={busy} onClick={() => editRubric(rubric)}>
                    {rubric.bloqueada ? 'Consultar' : 'Editar'}
                  </button>
                  <button type="button" disabled={busy} onClick={() => editRubric(rubric, true)}>
                    Duplicar
                  </button>
                </li>
              ))}
            </ul>
            <label className="field" htmlFor="rubric-source">
              Rubrica de um período anterior deste curso
              <select
                id="rubric-source"
                value={sourceId}
                disabled={busy || !source.length}
                onChange={(e) => setSourceId(e.target.value)}
              >
                <option value="">
                  {source.length ? 'Selecione a rubrica de origem' : 'Nenhuma rubrica anterior'}
                </option>
                {source.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.periodo} · {item.nome} · v{item.versao}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" disabled={busy || !sourceId} onClick={() => void importRubric()}>
              Importar como rascunho
            </button>
            <form onSubmit={(e) => void saveRubric(e)}>
              <h3>{rubricId ? 'Rubrica selecionada' : 'Nova rubrica'}</h3>
              <fieldset disabled={busy || currentRubric?.bloqueada}>
                <label className="field" htmlFor="rubric-name">
                  Nome
                  <input
                    id="rubric-name"
                    required
                    maxLength={150}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </label>
                {criteria.map((criterion, index) => (
                  <fieldset key={index} className="defense-criteria">
                    <legend>Critério {index + 1}</legend>
                    {(['nome', 'descricao', 'peso'] as const).map((field) => (
                      <label className="field" key={field} htmlFor={`criterion-${index}-${field}`}>
                        {
                          {
                            nome: 'Nome',
                            descricao: 'O que o avaliador deve observar',
                            peso: 'Peso',
                          }[field]
                        }
                        <input
                          id={`criterion-${index}-${field}`}
                          required
                          type={field === 'peso' ? 'number' : 'text'}
                          min={field === 'peso' ? 0.001 : undefined}
                          max={field === 'peso' ? 100 : undefined}
                          step={field === 'peso' ? '.001' : undefined}
                          maxLength={field === 'nome' ? 150 : 4000}
                          value={criterion[field]}
                          onChange={(e) =>
                            setCriteria(
                              criteria.map((item, i) =>
                                i === index ? { ...item, [field]: e.target.value } : item,
                              ),
                            )
                          }
                        />
                      </label>
                    ))}
                    <button
                      type="button"
                      disabled={criteria.length === 1}
                      onClick={() => setCriteria(criteria.filter((_, i) => i !== index))}
                    >
                      Remover critério {index + 1}
                    </button>
                  </fieldset>
                ))}
                <p aria-live="polite">
                  Soma dos pesos: {sum.toLocaleString('pt-BR')}. Para ativar, a soma deve ser 100 ou
                  10. Cada critério vale até 10.
                </p>
                <button
                  type="button"
                  onClick={() => setCriteria([...criteria, blankCriterion()])}
                  disabled={criteria.length >= 50}
                >
                  Adicionar critério
                </button>
                <label className="field" htmlFor="rubric-status">
                  Situação
                  <select
                    id="rubric-status"
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                  >
                    <option value="rascunho" disabled={currentRubric?.situacao === 'ativa'}>
                      Rascunho
                    </option>
                    <option value="ativa">Ativa</option>
                    <option value="inativa" disabled={currentRubric?.situacao === 'ativa'}>
                      Inativa
                    </option>
                  </select>
                </label>
                {currentRubric?.situacao === 'ativa' && (
                  <p>Para inativar esta rubrica, ative uma substituta.</p>
                )}
                {replacing && (
                  <label className="field">
                    <input
                      type="checkbox"
                      checked={replace}
                      onChange={(e) => setReplace(e.target.checked)}
                    />
                    Substituir a rubrica ativa {activeRubric.nome}
                  </label>
                )}
                <button className="primary" type="submit" disabled={Boolean(replacing && !replace)}>
                  Salvar rubrica
                </button>
              </fieldset>
              {rubricId && (
                <button type="button" onClick={resetRubric}>
                  Voltar para nova rubrica
                </button>
              )}
            </form>
          </>
        )}
      </div>
    </section>
  );
}
