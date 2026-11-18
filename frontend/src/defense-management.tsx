import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Notice } from './components';
import './defenses.css';

const dateTime = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Manaus',
  }).format(new Date(value));
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
type Work = {
  id: number;
  titulo: string;
  orientador: number;
  nome_orientador: string;
  estudante: string;
  nivel: number;
  manuscrito: boolean;
};
type Person = {
  id: number;
  nome: string;
  tipo: string;
  titulacao: string;
  instituicao: string | null;
};
type Booking = {
  id: number;
  titulo: string;
  etapa: number;
  rubrica: number;
  inicio: string;
  fim: string;
  modalidade: string;
  local: string;
  url: string | null;
  situacao: string;
  membros: { id: number; papel: string; nome: string }[];
};
type Scheduling = { trabalhos: Work[]; bancas: Booking[] };
const blankCriterion = (): Criterion => ({ nome: '', descricao: '', peso: '' });
const blankBooking = () => ({
  etapa: '',
  rubrica: '',
  inicio: '',
  fim: '',
  modalidade: 'presencial',
  local: '',
  url: '',
  titulares: [] as number[],
  suplentes: [] as number[],
});
const dateInput = (value: string) =>
  new Date(new Date(value).getTime() - 4 * 3600000).toISOString().slice(0, 16);

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
  const [schedule, setSchedule] = useState<Scheduling>({ trabalhos: [], bancas: [] });
  const [people, setPeople] = useState<Person[]>([]);
  const [known, setKnown] = useState<Record<number, string>>({});
  const [search, setSearch] = useState('');
  const [pick, setPick] = useState('');
  const [rubricId, setRubricId] = useState<number>();
  const [name, setName] = useState('');
  const [criteria, setCriteria] = useState([blankCriterion()]);
  const [status, setStatus] = useState('rascunho');
  const [replace, setReplace] = useState(false);
  const [bookingId, setBookingId] = useState<number>();
  const [booking, setBooking] = useState(blankBooking);
  const [mode, setMode] = useState<'rubricas' | 'bancas'>('rubricas');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [availability, setAvailability] = useState('');
  const externalDialog = useRef<HTMLDialogElement>(null);
  const [externalError, setExternalError] = useState('');
  const prefix = `/turmas/${classId}`;
  const currentWork = schedule.trabalhos.find((work) => String(work.id) === booking.etapa);
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
    const [rubricResult, bookingResult] = await Promise.all([
      api.request<Rubric[]>(`${prefix}/rubricas`, { signal }, true),
      api.request<Scheduling>(`${prefix}/bancas`, { signal }, true),
    ]);
    if (!signal?.aborted) {
      setRubrics(rubricResult.body.data);
      setSchedule(bookingResult.body.data);
    }
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
    if (!classId || mode !== 'bancas') return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .request<Person[]>(
          `${prefix}/avaliadores?q=${encodeURIComponent(search)}`,
          { signal: controller.signal },
          true,
        )
        .then(({ body }) => {
          if (controller.signal.aborted) return;
          setPeople(body.data);
          setKnown((previous) => ({
            ...previous,
            ...Object.fromEntries(body.data.map((p) => [p.id, p.nome])),
          }));
        })
        .catch((cause) => {
          if (!controller.signal.aborted) handleError(cause);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [classId, mode, search]);

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

  useEffect(() => {
    setAvailability('');
    if (
      mode !== 'bancas' ||
      !classId ||
      !booking.etapa ||
      !booking.inicio ||
      !booking.fim ||
      booking.inicio >= booking.fim ||
      booking.titulares.length + booking.suplentes.length > 19
    )
      return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setAvailability('Verificando conflitos de horário…');
      try {
        const { body } = await api.request<{ disponivel: boolean; conflitos: number[] }>(
          `${prefix}/bancas/disponibilidade`,
          {
            method: 'POST',
            signal: controller.signal,
            body: JSON.stringify({
              etapa: Number(booking.etapa),
              banca: bookingId,
              inicio: booking.inicio + ':00-04:00',
              fim: booking.fim + ':00-04:00',
              membros: [...booking.titulares, ...booking.suplentes],
            }),
          },
          true,
        );
        if (!controller.signal.aborted) {
          const names = body.data.conflitos
            .map((id) => (currentWork?.orientador === id ? currentWork.nome_orientador : known[id]))
            .filter(Boolean);
          setAvailability(
            body.data.disponivel
              ? 'Horário disponível para a composição selecionada.'
              : `Conflito de horário para ${names.join(', ') || 'a composição selecionada'}.`,
          );
        }
      } catch {
        if (!controller.signal.aborted)
          setAvailability('A disponibilidade será confirmada ao salvar.');
      }
    }, 350);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [classId, mode, booking, bookingId, currentWork, known]);

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

  async function openBooking(id: number) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const { body } = await api.request<Booking>(prefix + '/bancas/' + id, {}, true);
      editBooking(body.data);
    } catch (cause) {
      handleError(cause);
    } finally {
      setBusy(false);
    }
  }

  function editBooking(item: Booking) {
    setBookingId(item.id);
    setKnown((previous) => ({
      ...previous,
      ...Object.fromEntries(item.membros.map((p) => [p.id, p.nome])),
    }));
    setBooking({
      etapa: String(item.etapa),
      rubrica: String(item.rubrica),
      inicio: dateInput(item.inicio),
      fim: dateInput(item.fim),
      modalidade: item.modalidade,
      local: item.local,
      url: item.url || '',
      titulares: item.membros.filter((p) => p.papel === 'examinador').map((p) => p.id),
      suplentes: item.membros.filter((p) => p.papel === 'suplente').map((p) => p.id),
    });
    setError('');
  }

  async function save(event: FormEvent, kind: 'rubricas' | 'bancas') {
    event.preventDefault();
    setError('');
    setMessage('');
    if (kind === 'rubricas' && status === 'ativa' && sum !== 100 && sum !== 10) {
      setError('Para ativar a rubrica, ajuste a soma dos pesos para 100 ou 10.');
      return;
    }
    if (kind === 'bancas' && (booking.titulares.length < 2 || booking.suplentes.length < 1)) {
      setError('Adicione pelo menos dois titulares e um suplente. O orientador será o presidente.');
      return;
    }
    const id = kind === 'rubricas' ? rubricId : bookingId;
    const data =
      kind === 'rubricas'
        ? {
            nome: name,
            situacao: status,
            criterios: criteria,
            substituir: replacing && replace ? activeRubric.id : undefined,
          }
        : {
            ...booking,
            etapa: Number(booking.etapa),
            rubrica: Number(booking.rubrica),
            inicio: booking.inicio + ':00-04:00',
            fim: booking.fim + ':00-04:00',
          };
    setBusy(true);
    try {
      const { body } = await api.request(
        `${prefix}/${kind}${id ? `/${id}` : ''}`,
        {
          method: id ? 'PATCH' : 'POST',
          body: JSON.stringify(data),
        },
        true,
      );
      if (kind === 'rubricas') resetRubric();
      else {
        setBookingId(undefined);
        setBooking(blankBooking());
      }
      setMessage(kind === 'rubricas' ? 'Rubrica salva.' : body.message || 'Banca salva.');
      await load();
    } catch (cause) {
      handleError(cause);
    } finally {
      setBusy(false);
    }
  }

  function addMember(role: 'titulares' | 'suplentes') {
    const id = Number(pick);
    if (
      !id ||
      booking.titulares.includes(id) ||
      booking.suplentes.includes(id) ||
      currentWork?.orientador === id
    )
      return;
    setBooking({ ...booking, [role]: [...booking[role], id] });
    setPick('');
  }

  async function addExternal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const { papel, ...fields } = Object.fromEntries(new FormData(form));
    const role = papel === 'suplentes' ? 'suplentes' : 'titulares';
    setExternalError('');
    setError('');
    setMessage('');
    setBusy(true);
    try {
      const { body } = await api.request<Person>(
        `${prefix}/avaliadores/externos`,
        { method: 'POST', body: JSON.stringify(fields) },
        true,
      );
      const { id, nome } = body.data;
      setKnown((previous) => ({ ...previous, [id]: nome }));
      setBooking((previous) => ({ ...previous, [role]: [...previous[role], id] }));
      setMessage(`${nome} foi incluído na composição. Salve a banca para enviar o convite.`);
      form.reset();
      externalDialog.current?.close();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) onSessionEnded(cause.message);
      else setExternalError(failure(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="defense-portal defense-management">
      <div className="academic-box">
        <h2>Organizar defesas</h2>
        <p>Prepare os critérios da turma e agende a banca com o manuscrito mais recente.</p>
        <label className="field" htmlFor="def-class">
          Turma
          <select
            id="def-class"
            value={classId}
            disabled={busy}
            onChange={(e) => {
              setClassId(e.target.value);
              setRubrics([]);
              setSchedule({ trabalhos: [], bancas: [] });
              setSource([]);
              setSourceId('');
              resetRubric();
              setBookingId(undefined);
              setBooking(blankBooking());
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
        <div className="academic-actions" aria-label="Área de organização">
          <button
            type="button"
            aria-pressed={mode === 'rubricas'}
            disabled={busy}
            onClick={() => setMode('rubricas')}
          >
            Rubricas
          </button>
          <button
            type="button"
            aria-pressed={mode === 'bancas'}
            disabled={busy}
            onClick={() => setMode('bancas')}
          >
            Agendamentos
          </button>
        </div>
        {(loading || busy) && <p role="status">{busy ? 'Salvando…' : 'Carregando a turma…'}</p>}
        {error && <Notice message={error} />}
        {message && <Notice success message={message} />}
        {classId && !loading && mode === 'rubricas' && (
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
            <form onSubmit={(e) => void save(e, 'rubricas')}>
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
        {classId && !loading && mode === 'bancas' && (
          <>
            <h3>Bancas agendadas da turma</h3>
            {!schedule.bancas.length && <p>Nenhuma banca agendada nesta turma.</p>}
            <ul className="defense-records">
              {schedule.bancas.map((item) => (
                <li key={item.id}>
                  <strong>{item.titulo}</strong> · {dateTime(item.inicio)} · {item.local} ·{' '}
                  {item.situacao}
                  <button
                    type="button"
                    disabled={busy || item.situacao !== 'agendada'}
                    onClick={() => void openBooking(item.id)}
                  >
                    Editar banca
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={(e) => void save(e, 'bancas')}>
              <h3>{bookingId ? 'Editar agendamento' : 'Novo agendamento'}</h3>
              <fieldset disabled={busy}>
                <label className="field" htmlFor="booking-work">
                  Trabalho
                  <select
                    id="booking-work"
                    required
                    value={booking.etapa}
                    disabled={!!bookingId}
                    onChange={(e) =>
                      setBooking({
                        ...booking,
                        etapa: e.target.value,
                        titulares: [],
                        suplentes: [],
                      })
                    }
                  >
                    <option value="">Selecione um trabalho</option>
                    {schedule.trabalhos.map((work) => (
                      <option key={work.id} value={work.id}>
                        {work.titulo}
                        {!work.manuscrito && ' · aguardando manuscrito'}
                      </option>
                    ))}
                  </select>
                </label>
                {currentWork && (
                  <div>
                    <p>
                      {currentWork.estudante} · TCC {currentWork.nivel}
                    </p>
                    <p>Presidente da banca: {currentWork.nome_orientador}</p>
                    {currentWork.manuscrito ? (
                      <ManuscriptDownload
                        key={currentWork.id}
                        path={`${prefix}/etapas/${currentWork.id}/manuscrito`}
                        onSessionEnded={onSessionEnded}
                      />
                    ) : (
                      <p role="status">O estudante precisa enviar o manuscrito antes de agendar.</p>
                    )}
                  </div>
                )}
                <label className="field" htmlFor="booking-rubric">
                  Rubrica ativa
                  <select
                    id="booking-rubric"
                    required
                    value={booking.rubrica}
                    onChange={(e) => setBooking({ ...booking, rubrica: e.target.value })}
                  >
                    <option value="">Selecione a rubrica</option>
                    {rubrics
                      .filter((r) => r.situacao === 'ativa')
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.nome}
                        </option>
                      ))}
                  </select>
                </label>
                <p>
                  Horários de Manaus. O orientador aceito é incluído automaticamente como
                  presidente.
                </p>
                {(['inicio', 'fim'] as const).map((field) => (
                  <label className="field" key={field} htmlFor={`booking-${field}`}>
                    {field === 'inicio' ? 'Data e hora de início' : 'Data e hora de término'}
                    <input
                      type="datetime-local"
                      id={`booking-${field}`}
                      required
                      value={booking[field]}
                      onChange={(e) => setBooking({ ...booking, [field]: e.target.value })}
                    />
                  </label>
                ))}
                <label className="field" htmlFor="booking-mode">
                  Modalidade
                  <select
                    id="booking-mode"
                    value={booking.modalidade}
                    onChange={(e) => setBooking({ ...booking, modalidade: e.target.value })}
                  >
                    <option value="presencial">Presencial</option>
                    <option value="remota">Remota</option>
                    <option value="hibrida">Híbrida</option>
                  </select>
                </label>
                {booking.modalidade !== 'remota' && (
                  <label className="field" htmlFor="booking-room">
                    Local físico
                    <input
                      id="booking-room"
                      required
                      value={booking.local}
                      onChange={(e) => setBooking({ ...booking, local: e.target.value })}
                    />
                  </label>
                )}
                {booking.modalidade !== 'presencial' && (
                  <label className="field" htmlFor="booking-url">
                    Link da defesa
                    <input
                      id="booking-url"
                      type="url"
                      required
                      value={booking.url}
                      onChange={(e) => setBooking({ ...booking, url: e.target.value })}
                    />
                  </label>
                )}
                <label className="field" htmlFor="examiner-search">
                  Buscar avaliador pelo nome
                  <input
                    id="examiner-search"
                    type="search"
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setPick('');
                    }}
                  />
                </label>
                <label className="field" htmlFor="examiner-select">
                  Avaliador cadastrado
                  <select
                    id="examiner-select"
                    value={pick}
                    onChange={(e) => setPick(e.target.value)}
                  >
                    <option value="">Selecione uma pessoa</option>
                    {people
                      .filter(
                        (p) =>
                          p.id !== currentWork?.orientador &&
                          !booking.titulares.includes(p.id) &&
                          !booking.suplentes.includes(p.id),
                      )
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.nome} · {p.titulacao}
                          {p.instituicao ? ` · ${p.instituicao}` : ''}
                        </option>
                      ))}
                  </select>
                </label>
                <button type="button" disabled={!pick} onClick={() => addMember('titulares')}>
                  Adicionar titular
                </button>
                <button type="button" disabled={!pick} onClick={() => addMember('suplentes')}>
                  Adicionar suplente
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setExternalError('');
                    externalDialog.current?.showModal();
                  }}
                >
                  Adicionar membro externo
                </button>
                {(['titulares', 'suplentes'] as const).map((role) => (
                  <div key={role}>
                    <h4>{role === 'titulares' ? 'Titulares adicionais' : 'Suplentes'}</h4>
                    <ul className="defense-records">
                      {booking[role].map((id) => (
                        <li key={id}>
                          {known[id]}
                          <button
                            type="button"
                            aria-label={`Remover ${known[id]}`}
                            onClick={() =>
                              setBooking({
                                ...booking,
                                [role]: booking[role].filter((item) => item !== id),
                              })
                            }
                          >
                            Remover
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
                <p className="academic-hint" aria-live="polite">
                  {availability}
                </p>
                <button className="primary" type="submit" disabled={!currentWork?.manuscrito}>
                  {bookingId ? 'Salvar alterações e enviar convites' : 'Salvar e enviar convites'}
                </button>
                {bookingId && (
                  <button
                    type="button"
                    onClick={() => {
                      setBookingId(undefined);
                      setBooking(blankBooking());
                    }}
                  >
                    Cancelar edição
                  </button>
                )}
              </fieldset>
            </form>
            <dialog
              ref={externalDialog}
              aria-labelledby="external-title"
              onCancel={(event) => {
                if (busy) event.preventDefault();
              }}
            >
              <form onSubmit={(event) => void addExternal(event)}>
                <h3 id="external-title">Adicionar membro externo</h3>
                {externalError && <Notice message={externalError} />}
                <fieldset disabled={busy}>
                  <label className="field">
                    Nome completo <input name="nome" required maxLength={100} />
                  </label>
                  <label className="field">
                    E-mail institucional{' '}
                    <input name="email" type="email" required maxLength={254} />
                  </label>
                  <label className="field">
                    Titulação
                    <select name="titulacao" required defaultValue="">
                      <option value="">Selecione</option>
                      <option>Especialista</option>
                      <option>Mestre</option>
                      <option>Doutor</option>
                    </select>
                  </label>
                  <label className="field">
                    Instituição de origem <input name="instituicao" required maxLength={200} />
                  </label>
                  <label className="field">
                    Participação na banca
                    <select name="papel">
                      <option value="titulares">Titular</option>
                      <option value="suplentes">Suplente</option>
                    </select>
                  </label>
                  <button type="submit" className="primary">
                    Incluir na banca
                  </button>
                  <button type="button" onClick={() => externalDialog.current?.close()}>
                    Cancelar
                  </button>
                </fieldset>
                {busy && <p role="status">Cadastrando avaliador…</p>}
              </form>
            </dialog>
          </>
        )}
      </div>
    </section>
  );
}

function ManuscriptDownload({
  path,
  onSessionEnded,
}: {
  path: string;
  onSessionEnded: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function download() {
    setBusy(true);
    setError('');
    try {
      const { body } = await api.download(path);
      const url = URL.createObjectURL(body.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'manuscrito.pdf';
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) onSessionEnded(cause.message);
      else setError(failure(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button type="button" disabled={busy} onClick={() => void download()}>
        {busy ? 'Baixando…' : 'Baixar manuscrito (PDF)'}
      </button>
      {error && <Notice message={error} />}
    </>
  );
}

export function ManuscriptAccess({
  onSessionEnded,
}: {
  onSessionEnded: (message: string) => void;
}) {
  const id = new URLSearchParams(window.location.hash.split('?')[1]).get('banca');
  return (
    <section className="academic-box">
      <h2>Manuscrito da defesa</h2>
      {id && /^[1-9][0-9]*$/.test(id) ? (
        <ManuscriptDownload path={`/bancas/${id}/manuscrito`} onSessionEnded={onSessionEnded} />
      ) : (
        <Notice message="Abra o link do manuscrito no convite da banca." />
      )}
    </section>
  );
}

export function ManuscriptUpload({ stage }: { stage: number }) {
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  async function send() {
    if (!file) return;
    setError('');
    setMessage('');
    if (file.size > 50 * 1024 * 1024 || !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Selecione um PDF de até 50 MB.');
      return;
    }
    setBusy(true);
    try {
      const data = new FormData();
      data.set('arquivo', file);
      const { body } = await api.request<{ versao: number }>(
        `/etapas/${stage}/manuscritos`,
        { method: 'POST', body: data },
        true,
      );
      setMessage(`Manuscrito recebido. Versão ${body.data.versao}.`);
    } catch (cause) {
      setError(failure(cause));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="academic-box defense-criteria">
      <h3>Manuscrito para a banca</h3>
      <label className="field" htmlFor="work-manuscript">
        PDF de até 50 MB
        <input
          id="work-manuscript"
          type="file"
          accept="application/pdf,.pdf"
          disabled={busy}
          onChange={(e) => {
            setFile(e.target.files?.[0]);
            setError('');
            setMessage('');
          }}
        />
      </label>
      <button type="button" disabled={!file || busy} onClick={() => void send()}>
        {busy ? 'Enviando…' : 'Enviar manuscrito'}
      </button>
      {message && <Notice success message={message} />}
      {error && <Notice message={error} />}
    </div>
  );
}
