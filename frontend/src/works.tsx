import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import type { Course } from './types';
import type { Enrollment } from './enrollments';
import { Notice } from './components';
import {
  AcademicField,
  catalog,
  failure,
  fieldProps,
  Pager,
  sessionError,
  type SessionProps,
} from './academic';

interface Orientation {
  id_orientacao: number;
  id_docente: number;
  nome: string;
  papel: string;
  situacao: string;
  data_resposta: string | null;
}
export interface Work {
  id_trabalho: number;
  titulo: string;
  subtitulo: string | null;
  tema: string;
  modalidade: string;
  tipo_artigo: string | null;
  url: string | null;
  doi: string | null;
  id_curso: number;
  id_matricula: number | null;
  id_etapa: number | null;
  nivel_turma: number | null;
  codigo_turma: string | null;
  palavras_chave: string[];
  aluno: string;
  situacao: string;
  orientacoes: Orientation[];
}
interface Teacher {
  id_docente: number;
  nome: string;
}
const empty = {
  titulo: '',
  subtitulo: '',
  tema: '',
  modalidade: 'monografia',
  tipo_artigo: '',
  url: '',
  doi: '',
  id_curso: '',
  id_matricula: '',
  id_orientador: '',
  id_coorientador: '',
  palavras_chave: '',
};
export function Works({ onSessionEnded }: SessionProps) {
  const [own, setOwn] = useState<boolean | null>(null),
    [userId, setUserId] = useState(0),
    [work, setWork] = useState<Work | null>(null),
    [list, setList] = useState<Work[]>([]),
    [etag, setEtag] = useState('');
  const [courses, setCourses] = useState<Course[]>([]),
    [enrollments, setEnrollments] = useState<Enrollment[]>([]),
    [teachers, setTeachers] = useState<Teacher[]>([]),
    [values, setValues] = useState(empty);
  const [message, setMessage] = useState(''),
    [success, setSuccess] = useState(''),
    [errors, setErrors] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false),
    [attempt, setAttempt] = useState(0),
    [page, setPage] = useState(1),
    [pages, setPages] = useState(1);
  function error(e: unknown) {
    setMessage(failure(e));
    sessionError(e, onSessionEnded);
    if (e instanceof ApiError) setErrors(e.fields);
  }
  function apply(item: Work | null, version: string) {
    setWork(item);
    setEtag(version);
    if (item)
      setValues({
        titulo: item.titulo,
        subtitulo: item.subtitulo || '',
        tema: item.tema || '',
        modalidade: item.modalidade,
        tipo_artigo: item.tipo_artigo || '',
        url: item.url || '',
        doi: item.doi || '',
        id_curso: String(item.id_curso),
        id_matricula: item.id_matricula ? String(item.id_matricula) : '',
        id_orientador: String(
          item.orientacoes.find((o) => o.papel === 'orientador')?.id_docente || '',
        ),
        id_coorientador: String(
          item.orientacoes.find((o) => o.papel === 'coorientador')?.id_docente || '',
        ),
        palavras_chave: item.palavras_chave.join(', '),
      });
  }
  useEffect(() => {
    let active = true;
    setBusy(true);
    (async () => {
      const profile = (await api.profile()).body.data;
      if (!active) return;
      setOwn(!!profile.aluno);
      setUserId(profile.id_usuario);
      if (profile.aluno) {
        const [courses, members, teachers, current] = await Promise.all([
          api.courses(),
          catalog<Enrollment>('/minhas-matriculas'),
          catalog<Teacher>('/docentes-orientacao'),
          api.request<Work | null>('/meu-trabalho', {}, true),
        ]);
        if (!active) return;
        setCourses(courses);
        setEnrollments(members.filter((m) => m.turma_ativa));
        setTeachers(teachers);
        setValues({ ...empty, id_curso: String(profile.aluno.id_curso) });
        apply(current.body.data, current.etag || '');
      } else {
        const r = await api.request<Work[]>(`/orientacoes?page=${page}&per_page=20`, {}, true);
        if (active) {
          setList(r.body.data);
          setPages(r.body.meta?.pages || 1);
        }
      }
    })()
      .catch((e) => {
        if (active) error(e);
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [attempt, page]);
  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage('');
    setSuccess('');
    const invalid: Record<string, string> = {};
    for (const key of ['titulo', 'tema', 'id_matricula', 'id_orientador'] as const)
      if (!values[key].trim()) invalid[key] = 'Obrigatório.';
    if (values.modalidade === 'artigo') {
      if (!values.tipo_artigo)
        invalid.tipo_artigo = 'Informe se o artigo é Publicado ou A Submeter.';
      if (values.tipo_artigo === 'publicado') {
        if (!values.url.trim()) invalid.url = 'Obrigatório para artigo publicado.';
        if (!values.doi.trim()) invalid.doi = 'Obrigatório para artigo publicado.';
      }
    }
    setErrors(invalid);
    if (Object.keys(invalid).length) {
      setMessage('Preencha os campos obrigatórios indicados.');
      return;
    }
    setBusy(true);
    try {
      const r = await api.request<Work>(
        '/meu-trabalho',
        {
          method: 'PUT',
          headers: work ? { 'If-Match': etag } : {},
          body: JSON.stringify({
            ...values,
            id_curso: Number(values.id_curso),
            id_matricula: Number(values.id_matricula),
            id_orientador: Number(values.id_orientador),
            id_coorientador: values.id_coorientador ? Number(values.id_coorientador) : null,
            palavras_chave: values.palavras_chave
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
          }),
        },
        true,
      );
      apply(r.body.data, r.etag || '');
      setSuccess('Trabalho registrado com sucesso!');
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function open(id: number) {
    setMessage('');
    setSuccess('');
    setBusy(true);
    try {
      const r = await api.request<Work>(`/orientacoes/${id}`, {}, true);
      apply(r.body.data, r.etag || '');
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function respond(id: number, decision: string) {
    setMessage('');
    setBusy(true);
    try {
      const r = await api.request<Work>(
        `/orientacoes/${id}/resposta`,
        {
          method: 'POST',
          headers: { 'If-Match': etag },
          body: JSON.stringify({ decisao: decision }),
        },
        true,
      );
      apply(r.body.data, r.etag || '');
      setSuccess('Resposta de orientação registrada.');
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  const membership = enrollments.find((m) => String(m.id_matricula) === values.id_matricula);
  function input(key: keyof typeof empty, label: string, maxLength = 500) {
    return (
      <AcademicField key={key} name={key} label={label} error={errors[key]}>
        <input
          {...fieldProps(key, errors)}
          value={values[key]}
          onChange={(e) => setValues({ ...values, [key]: e.target.value })}
          maxLength={maxLength}
          disabled={busy}
        />
      </AcademicField>
    );
  }
  function teacherSelect(key: 'id_orientador' | 'id_coorientador', label: string, role: string) {
    return (
      <AcademicField name={key} label={label} error={errors[key]}>
        <select
          id={key}
          aria-invalid={!!errors[key]}
          value={values[key]}
          onChange={(e) => setValues({ ...values, [key]: e.target.value })}
          disabled={busy || !!work?.orientacoes.some((o) => o.papel === role)}
        >
          <option value="">{role === 'orientador' ? 'Selecione docente ativo' : 'Nenhum'}</option>
          {teachers.map((t) => (
            <option key={t.id_docente} value={t.id_docente}>
              {t.nome}
            </option>
          ))}
        </select>
      </AcademicField>
    );
  }
  return (
    <section>
      <div className="page-intro">
        <span className="eyebrow">PESQUISA E ORIENTAÇÃO</span>
        <h2>{own ? 'Meu trabalho' : 'Trabalhos'}</h2>
        <p>
          {own
            ? 'Registre seu TCC e acompanhe os vínculos de orientação.'
            : 'Consulte os trabalhos para os quais você foi indicado e responda ao vínculo.'}
        </p>
      </div>
      {message && (
        <Notice message={message}>
          <button
            className="text-button"
            onClick={() => {
              setMessage('');
              setAttempt(attempt + 1);
            }}
          >
            Recarregar dados
          </button>
        </Notice>
      )}
      {success && <Notice success message={success} />}
      {own === null && <p aria-live="polite">Carregando trabalhos…</p>}
      {own && (
        <form className="academic-box" aria-label="Dados do trabalho" onSubmit={save} noValidate>
          <h3>Dados do TCC</h3>
          <div className="academic-grid">
            {input('titulo', 'Título do trabalho')}
            {input('subtitulo', 'Subtítulo (opcional)')}
            <AcademicField name="id_curso" label="Curso do estudante">
              <select id="id_curso" value={values.id_curso} disabled>
                {courses.map((c) => (
                  <option key={c.id_curso} value={c.id_curso}>
                    {c.nome_curso}
                  </option>
                ))}
              </select>
            </AcademicField>
            <AcademicField name="id_matricula" label="Turma vinculada" error={errors.id_matricula}>
              <select
                id="id_matricula"
                aria-invalid={!!errors.id_matricula}
                value={values.id_matricula}
                onChange={(e) => setValues({ ...values, id_matricula: e.target.value })}
                disabled={busy}
                required
              >
                <option value="">Selecione sua matrícula ativa</option>
                {enrollments.map((m) => (
                  <option key={m.id_matricula} value={m.id_matricula}>
                    {m.codigo_turma} · {m.periodo_letivo}
                  </option>
                ))}
              </select>
            </AcademicField>
            <AcademicField name="nivel-trabalho" label="Nível da disciplina">
              <input
                id="nivel-trabalho"
                value={membership ? `TCC ${membership.nivel_turma}` : 'Aguardando matrícula válida'}
                readOnly
              />
            </AcademicField>
            {input('tema', 'Área de interesse / Tema', 5000)}
            <AcademicField name="modalidade" label="Modalidade do trabalho">
              <select
                id="modalidade"
                value={values.modalidade}
                onChange={(e) =>
                  setValues({
                    ...values,
                    modalidade: e.target.value,
                    tipo_artigo: '',
                    url: '',
                    doi: '',
                  })
                }
                disabled={busy}
              >
                <option value="monografia">Monografia</option>
                <option value="artigo">Artigo</option>
              </select>
            </AcademicField>
            {values.modalidade === 'artigo' && (
              <AcademicField name="tipo_artigo" label="Tipo de artigo" error={errors.tipo_artigo}>
                <select
                  id="tipo_artigo"
                  aria-invalid={!!errors.tipo_artigo}
                  value={values.tipo_artigo}
                  onChange={(e) => setValues({ ...values, tipo_artigo: e.target.value })}
                  disabled={busy}
                  required
                >
                  <option value="">Selecione</option>
                  <option value="publicado">Publicado</option>
                  <option value="a_submeter">A Submeter</option>
                </select>
              </AcademicField>
            )}
            {values.modalidade === 'artigo' && values.tipo_artigo === 'publicado' && (
              <>
                {input('url', 'Link/URL do artigo', 2048)}
                {input('doi', 'DOI do artigo', 255)}
              </>
            )}
            {teacherSelect('id_orientador', 'Orientador', 'orientador')}
            {teacherSelect('id_coorientador', 'Coorientador (opcional)', 'coorientador')}
            {input('palavras_chave', 'Palavras-chave (opcional, separadas por vírgula)', 1100)}
          </div>
          {!enrollments.length && (
            <p className="academic-hint">
              Não há matrícula em turma ativa. Regularize seu vínculo em{' '}
              <a href="#/matriculas">Matrículas</a> ou com o professor; o nível não pode ser
              digitado manualmente.
            </p>
          )}
          <p className="academic-hint">
            O curso vem do seu cadastro e o nível vem da turma. O docente receberá uma notificação e
            deverá responder ao vínculo. Trocas de orientação exigem o fluxo autorizado do RF05.
          </p>
          <div className="academic-actions">
            <button className="primary" disabled={busy}>
              {busy ? 'Salvando…' : 'Salvar trabalho'}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => setAttempt(attempt + 1)}
              disabled={busy}
            >
              Recarregar trabalho e vínculos
            </button>
          </div>
        </form>
      )}
      {own === false && !work && (
        <>
          <div className="academic-list">
            {list.map((w) => (
              <article className="academic-box" key={w.id_trabalho}>
                <h3>{w.titulo}</h3>
                <p>{w.aluno}</p>
                <button className="secondary" onClick={() => open(w.id_trabalho)}>
                  Abrir {w.titulo}
                </button>
              </article>
            ))}
          </div>
          {!list.length && !busy && <p className="academic-empty">Nenhum trabalho vinculado.</p>}
          <Pager page={page} pages={pages} onChange={setPage} />
        </>
      )}
      {work && (
        <div className="academic-box">
          <h3>Vínculos de orientação</h3>
          {!own && (
            <>
              <h4>{work.titulo}</h4>
              <p>
                {work.aluno} · {work.codigo_turma || 'Turma não informada'}
              </p>
              <p className="academic-summary">{work.tema}</p>
            </>
          )}
          {work.orientacoes.map((o) => (
            <article key={o.id_orientacao}>
              <h4>
                {o.nome} · {o.papel}
              </h4>
              <p>
                Situação: {o.situacao}
                {o.data_resposta ? ` · ${new Date(o.data_resposta).toLocaleString('pt-BR')}` : ''}
              </p>
              {!own && o.id_docente === userId && o.situacao === 'pendente' && (
                <div className="academic-actions">
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() => respond(o.id_orientacao, 'aceito')}
                  >
                    Aceitar orientação
                  </button>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => respond(o.id_orientacao, 'recusado')}
                  >
                    Recusar orientação
                  </button>
                </div>
              )}
            </article>
          ))}
          {!own && (
            <button
              className="text-button"
              onClick={() => {
                setWork(null);
                setAttempt(attempt + 1);
              }}
            >
              Voltar aos trabalhos
            </button>
          )}
        </div>
      )}
    </section>
  );
}
