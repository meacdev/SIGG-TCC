import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Notice } from './components';
import { catalog, failure, Pager, sessionError, type SessionProps } from './academic';

interface Stage {
  id_etapa: number;
  titulo: string;
  aluno: string;
  codigo_turma: string;
  nivel_turma: number;
  pode_registrar: boolean;
}
interface Meeting {
  id_reuniao: number;
  data_encontro: string;
  resumo: string;
  orientador: string;
  autor: string;
  data_registro: string;
}
interface Attendance {
  id_matricula: number;
  id_etapa: number | null;
  aluno: string;
  matricula: string;
  codigo_turma: string;
  titulo: string | null;
  quantidade_reunioes: number;
  ultimo_encontro: string | null;
  dias_sem_reuniao: number;
  alerta_inatividade: boolean;
}
export function Meetings({ onSessionEnded }: SessionProps) {
  const [stages, setStages] = useState<Stage[]>([]),
    [selected, setSelected] = useState(''),
    [rows, setRows] = useState<Meeting[]>([]),
    [overview, setOverview] = useState<Attendance[]>([]),
    [teacher, setTeacher] = useState(false);
  const [date, setDate] = useState(''),
    [summary, setSummary] = useState(''),
    [message, setMessage] = useState(''),
    [success, setSuccess] = useState(''),
    [busy, setBusy] = useState(false),
    [attempt, setAttempt] = useState(0),
    [page, setPage] = useState(1),
    [pages, setPages] = useState(1),
    [reportPage, setReportPage] = useState(1),
    [reportPages, setReportPages] = useState(1),
    [errors, setErrors] = useState<Record<string, string>>({});
  function error(e: unknown) {
    setMessage(failure(e));
    sessionError(e, onSessionEnded);
    if (e instanceof ApiError) setErrors(e.fields);
  }
  useEffect(() => {
    let active = true;
    catalog<Stage>('/trabalhos-reunioes')
      .then((data) => {
        if (active) setStages(data);
      })
      .catch(error);
    api
      .profile()
      .then((r) => {
        if (active)
          setTeacher(
            r.body.data.perfis.some((p) => ['professor_disciplina', 'coordenador'].includes(p)),
          );
      })
      .catch(error);
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    if (!selected) {
      setRows([]);
      return;
    }
    setBusy(true);
    api
      .request<Meeting[]>(`/etapas/${selected}/reunioes?page=${page}&per_page=20`, {}, true)
      .then((r) => {
        if (active) {
          setRows(r.body.data);
          setPages(r.body.meta?.pages || 1);
        }
      })
      .catch((e) => {
        if (active) error(e);
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [selected, page, attempt]);
  useEffect(() => {
    let active = true;
    if (teacher)
      api
        .request<Attendance[]>(`/acompanhamento-reunioes?page=${reportPage}&per_page=20`, {}, true)
        .then((r) => {
          if (active) {
            setOverview(r.body.data);
            setReportPages(r.body.meta?.pages || 1);
          }
        })
        .catch((e) => {
          if (active) error(e);
        });
    return () => {
      active = false;
    };
  }, [teacher, reportPage, attempt]);
  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage('');
    setSuccess('');
    const invalid: Record<string, string> = {};
    if (!date.trim()) invalid.data_encontro = 'Obrigatório.';
    if (!summary.trim()) invalid.resumo = 'Obrigatório.';
    setErrors(invalid);
    if (Object.keys(invalid).length) {
      setMessage('Preencha os campos obrigatórios indicados.');
      return;
    }
    setBusy(true);
    try {
      await api.request<Meeting>(
        `/etapas/${selected}/reunioes`,
        { method: 'POST', body: JSON.stringify({ data_encontro: date, resumo: summary }) },
        true,
      );
      setSuccess('Ata registrada com sucesso!');
      setSummary('');
      setDate('');
      setAttempt(attempt + 1);
      setPage(1);
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  const stage = stages.find((s) => String(s.id_etapa) === selected);
  function choose(value: string) {
    setSelected(value);
    setPage(1);
    setMessage('');
    setSuccess('');
    setErrors({});
    setDate('');
    setSummary('');
  }
  return (
    <section>
      <div className="page-intro">
        <span className="eyebrow">HISTÓRICO DA ORIENTAÇÃO</span>
        <h2>Reuniões</h2>
        <p>Registre os encontros e acompanhe os encaminhamentos do trabalho.</p>
      </div>
      {message && <Notice message={message} />} {success && <Notice success message={success} />}
      <div className="field">
        <label htmlFor="trabalho-reuniao">Trabalho vinculado</label>
        <select id="trabalho-reuniao" value={selected} onChange={(e) => choose(e.target.value)}>
          <option value="">Selecione um trabalho</option>
          {stages.map((s) => (
            <option key={s.id_etapa} value={s.id_etapa}>
              {s.titulo} · {s.aluno} · {s.codigo_turma}
            </option>
          ))}
        </select>
      </div>
      {!stages.length && (
        <p className="academic-empty">
          Nenhum trabalho vinculado disponível. O estudante precisa estar matriculado e ter um
          trabalho cadastrado; o orientador precisa aceitar o vínculo para registrar atas.
        </p>
      )}
      {stage && (
        <>
          <div className="academic-box">
            <h3>{stage.titulo}</h3>
            <p>
              {stage.aluno} · {stage.codigo_turma} · TCC {stage.nivel_turma}
            </p>
          </div>
          {stage.pode_registrar ? (
            <form
              className="academic-box"
              aria-label="Registrar ata de reunião"
              onSubmit={save}
              noValidate
            >
              <h3>Nova ata de reunião</h3>
              <div className="field">
                <label htmlFor="data-encontro">Data do encontro</label>
                <input
                  id="data-encontro"
                  placeholder="DD/MM/AAAA"
                  maxLength={10}
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  disabled={busy}
                  aria-invalid={!!errors.data_encontro}
                  aria-describedby={errors.data_encontro ? 'erro-data-encontro' : undefined}
                  required
                />
                {errors.data_encontro && (
                  <small className="field-error" id="erro-data-encontro">
                    {errors.data_encontro}
                  </small>
                )}
              </div>
              <div className="field">
                <label htmlFor="resumo-reuniao">Resumo dos encaminhamentos</label>
                <textarea
                  id="resumo-reuniao"
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  disabled={busy}
                  maxLength={10000}
                  aria-invalid={!!errors.resumo}
                  required
                />
                {errors.resumo && <small className="field-error">{errors.resumo}</small>}
              </div>
              <p className="academic-hint">
                A ata será preservada no histórico. Estudante e orientador recebem uma notificação
                por e-mail. Para corrigir um registro, acrescente uma nova ata explicando a
                correção.
              </p>
              <div className="academic-actions">
                <button className="primary" disabled={busy}>
                  {busy ? 'Registrando…' : 'Registrar ata'}
                </button>
              </div>
            </form>
          ) : (
            <p className="academic-hint">
              Consulta do histórico. Novos registros exigem matrícula ativa e orientação aceita;
              professor da disciplina consulta as atas de suas turmas.
            </p>
          )}
          <h3>Atas registradas</h3>
          {busy && <p aria-live="polite">Carregando…</p>}
          {!rows.length && !busy && (
            <p className="academic-empty">Nenhuma ata registrada para esta etapa.</p>
          )}
          <div className="academic-list">
            {rows.map((r) => (
              <article className="academic-box" key={r.id_reuniao}>
                <h3>Encontro de {r.data_encontro}</h3>
                <p className="academic-summary">{r.resumo}</p>
                <p className="academic-hint">
                  Orientador: {r.orientador}
                  <br />
                  Registrada por {r.autor} em {new Date(r.data_registro).toLocaleString('pt-BR')}.
                </p>
              </article>
            ))}
          </div>
          <Pager page={page} pages={pages} onChange={setPage} />
        </>
      )}
      {teacher && (
        <div className="academic-box">
          <h3>Assiduidade das minhas turmas</h3>
          <p className="academic-hint">
            Sem encontro registrado, os dias são contados desde a matrícula. O alerta aparece após
            mais de 30 dias.
          </p>
          <div className="academic-list">
            {overview.map((r) => (
              <article className="academic-box" key={r.id_matricula}>
                <h4>
                  {r.aluno} · {r.codigo_turma}
                </h4>
                <p>
                  {r.quantidade_reunioes} {r.quantidade_reunioes === 1 ? 'reunião' : 'reuniões'} ·
                  Último encontro: {r.ultimo_encontro || 'Nenhum'}
                </p>
                <p>
                  {r.dias_sem_reuniao} dias sem reunião
                  {r.alerta_inatividade ? ' · Alerta: mais de 30 dias sem encontro' : ''}
                </p>
                {!r.id_etapa && <p className="academic-hint">Trabalho ainda não cadastrado.</p>}
                {r.id_etapa && (
                  <button className="secondary" onClick={() => choose(String(r.id_etapa))}>
                    Ver histórico de {r.aluno}
                  </button>
                )}
              </article>
            ))}
          </div>
          {!overview.length && (
            <p>Nenhum estudante matriculado nas turmas sob sua responsabilidade.</p>
          )}
          <Pager page={reportPage} pages={reportPages} onChange={setReportPage} />
        </div>
      )}
    </section>
  );
}
