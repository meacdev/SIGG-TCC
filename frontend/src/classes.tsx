import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import type { Course } from './types';
import { Notice } from './components';
import {
  AcademicField,
  catalog,
  ConfirmDialog,
  failure,
  fieldProps,
  Pager,
  sessionError,
  type SessionProps,
} from './academic';

export interface ClassItem {
  id_turma: number;
  codigo_turma: string;
  periodo_letivo: string;
  nivel_turma: number;
  id_curso: number;
  id_docente_responsavel: number;
  ativa_turma: boolean;
  autoinscricao_ativa_turma: boolean;
  data_expiracao_acesso_turma: string | null;
  codigo_acesso?: string;
}
interface Teacher {
  id_docente: number;
  nome_usuario: string;
}
const empty = {
  periodo_letivo: '',
  codigo_turma: '',
  nivel_turma: '',
  id_curso: '',
  id_docente_responsavel: '',
};
export function Classes({ onSessionEnded }: SessionProps) {
  const [items, setItems] = useState<ClassItem[]>([]),
    [courses, setCourses] = useState<Course[]>([]),
    [teachers, setTeachers] = useState<Teacher[]>([]);
  const [values, setValues] = useState(empty),
    [selected, setSelected] = useState<ClassItem | null>(null),
    [etag, setEtag] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({}),
    [message, setMessage] = useState(''),
    [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [accessCode, setAccessCode] = useState(''),
    [confirm, setConfirm] = useState(false);
  const [page, setPage] = useState(1),
    [pages, setPages] = useState(1),
    [attempt, setAttempt] = useState(0),
    [filter, setFilter] = useState('true');
  function error(error: unknown) {
    setMessage(failure(error));
    sessionError(error, onSessionEnded);
    if (error instanceof ApiError) setErrors(error.fields);
  }
  useEffect(() => {
    let active = true;
    api
      .courses()
      .then((data) => {
        if (active) setCourses(data);
      })
      .catch(error);
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .request<ClassItem[]>(
        `/turmas?page=${page}&per_page=20${filter ? `&ativa_turma=${filter}` : ''}`,
        {},
        true,
      )
      .then((r) => {
        if (active) {
          setItems(r.body.data);
          setPages(r.body.meta?.pages || 1);
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
  }, [page, attempt, filter]);
  useEffect(() => {
    let active = true;
    setTeachers([]);
    if (values.id_curso)
      catalog<Teacher>(`/docentes?id_curso=${values.id_curso}`)
        .then((data) => {
          if (active) setTeachers(data);
        })
        .catch((e) => {
          if (active) error(e);
        });
    return () => {
      active = false;
    };
  }, [values.id_curso]);
  function reset() {
    setSelected(null);
    setEtag('');
    setValues(empty);
    setErrors({});
    setAccessCode('');
    setMessage('');
    setSuccess('');
  }
  async function open(id: number) {
    setBusy(true);
    setMessage('');
    setSuccess('');
    setAccessCode('');
    try {
      const r = await api.request<ClassItem>(`/turmas/${id}`, {}, true);
      const v = r.body.data;
      setSelected(v);
      setEtag(r.etag || '');
      setValues({
        periodo_letivo: v.periodo_letivo,
        codigo_turma: v.codigo_turma,
        nivel_turma: String(v.nivel_turma),
        id_curso: String(v.id_curso),
        id_docente_responsavel: String(v.id_docente_responsavel),
      });
      setErrors({});
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage('');
    setSuccess('');
    const invalid: Record<string, string> = {};
    for (const [key, value] of Object.entries(values))
      if (!value.trim()) invalid[key] = 'Obrigatório.';
    if (values.periodo_letivo && !/^[0-9]{4}\/[12]$/.test(values.periodo_letivo))
      invalid.periodo_letivo = 'Informe AAAA/1 ou AAAA/2.';
    if (values.codigo_turma && !/^EST[A-Z]+[0-9]+$/i.test(values.codigo_turma))
      invalid.codigo_turma = 'Use EST<SIGLA><NUM>, por exemplo ESTCOMP01.';
    setErrors(invalid);
    if (Object.keys(invalid).length) {
      setMessage('Preencha os campos obrigatórios indicados e confira o formato.');
      return;
    }
    setBusy(true);
    try {
      const r = await api.request<ClassItem>(
        selected ? `/turmas/${selected.id_turma}` : '/turmas',
        {
          method: selected ? 'PATCH' : 'POST',
          headers: selected ? { 'If-Match': etag } : {},
          body: JSON.stringify({
            ...values,
            nivel_turma: Number(values.nivel_turma),
            id_curso: Number(values.id_curso),
            id_docente_responsavel: Number(values.id_docente_responsavel),
          }),
        },
        true,
      );
      setSelected(r.body.data);
      setEtag(r.etag || '');
      setAccessCode(r.body.data.codigo_acesso || '');
      setSuccess(selected ? 'Turma atualizada com sucesso!' : 'Turma cadastrada com sucesso!');
      setAttempt(attempt + 1);
    } catch (e) {
      error(e);
      if (e instanceof ApiError && e.code === 'TURMA_DUPLICADA')
        setErrors({ codigo_turma: e.message, periodo_letivo: e.message });
    } finally {
      setBusy(false);
    }
  }
  async function action(kind: 'codigo' | 'inativar' | 'reativar' | 'autoinscricao') {
    if (!selected || busy) return;
    setBusy(true);
    setMessage('');
    setSuccess('');
    try {
      const r = await api.request<ClassItem>(
        `/turmas/${selected.id_turma}${kind === 'codigo' ? '/codigo-acesso' : ''}`,
        {
          method: kind === 'codigo' ? 'POST' : kind === 'inativar' ? 'DELETE' : 'PATCH',
          headers: { 'If-Match': etag },
          ...(kind === 'reativar'
            ? { body: JSON.stringify({ ativa_turma: true }) }
            : kind === 'autoinscricao'
              ? {
                  body: JSON.stringify({
                    autoinscricao_ativa_turma: !selected.autoinscricao_ativa_turma,
                  }),
                }
              : {}),
        },
        true,
      );
      if (kind === 'inativar') {
        reset();
        setSuccess('Turma inativada com sucesso!');
      } else {
        setSelected(r.body.data);
        setEtag(r.etag || '');
        setAccessCode(r.body.data.codigo_acesso || '');
        setSuccess('Turma atualizada com sucesso!');
      }
      setAttempt(attempt + 1);
      setConfirm(false);
    } catch (e) {
      error(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <div className="page-intro">
        <span className="eyebrow">ORGANIZAÇÃO DO SEMESTRE</span>
        <h2>Turmas</h2>
        <p>Cadastre as ofertas de TCC e acompanhe as turmas sob sua responsabilidade.</p>
      </div>
      {message && (
        <Notice message={message}>
          {selected && (
            <button className="text-button" onClick={() => open(selected.id_turma)}>
              Recarregar turma
            </button>
          )}
        </Notice>
      )}
      {success && <Notice success message={success} />}
      <form className="academic-box" onSubmit={save} noValidate aria-label="Cadastro de turma">
        <h3>{selected ? 'Editar turma' : 'Nova turma'}</h3>
        <div className="academic-grid">
          <AcademicField
            name="periodo_letivo"
            label="Ano/Semestre letivo"
            error={errors.periodo_letivo}
          >
            <input
              {...fieldProps('periodo_letivo', errors)}
              placeholder="2026/2"
              value={values.periodo_letivo}
              onChange={(e) => setValues({ ...values, periodo_letivo: e.target.value })}
              disabled={busy}
              required
            />
          </AcademicField>
          <AcademicField name="nivel_turma" label="Disciplina" error={errors.nivel_turma}>
            <select
              id="nivel_turma"
              aria-invalid={!!errors.nivel_turma}
              value={values.nivel_turma}
              onChange={(e) => setValues({ ...values, nivel_turma: e.target.value })}
              disabled={busy}
              required
            >
              <option value="">Selecione</option>
              <option value="1">TCC 1</option>
              <option value="2">TCC 2</option>
            </select>
          </AcademicField>
          <AcademicField name="codigo_turma" label="Código da turma" error={errors.codigo_turma}>
            <input
              {...fieldProps('codigo_turma', errors)}
              placeholder="ESTCOMP01"
              maxLength={40}
              value={values.codigo_turma}
              onChange={(e) => setValues({ ...values, codigo_turma: e.target.value.toUpperCase() })}
              disabled={busy}
              required
            />
          </AcademicField>
          <AcademicField name="id_curso" label="Curso da turma" error={errors.id_curso}>
            <select
              id="id_curso"
              aria-invalid={!!errors.id_curso}
              value={values.id_curso}
              onChange={(e) => {
                setValues({ ...values, id_curso: e.target.value, id_docente_responsavel: '' });
                setMessage('');
              }}
              disabled={busy || !courses.length}
              required
            >
              <option value="">Selecione</option>
              {courses.map((c) => (
                <option key={c.id_curso} value={c.id_curso}>
                  {c.nome_curso}
                </option>
              ))}
            </select>
          </AcademicField>
          <AcademicField
            name="id_docente_responsavel"
            label="Docente responsável"
            error={errors.id_docente_responsavel}
          >
            <select
              id="id_docente_responsavel"
              aria-invalid={!!errors.id_docente_responsavel}
              value={values.id_docente_responsavel}
              onChange={(e) => setValues({ ...values, id_docente_responsavel: e.target.value })}
              disabled={busy || !teachers.length}
              required
            >
              <option value="">
                {teachers.length ? 'Selecione' : 'Selecione um curso com docentes autorizados'}
              </option>
              {teachers.map((t) => (
                <option key={t.id_docente} value={t.id_docente}>
                  {t.nome_usuario}
                </option>
              ))}
            </select>
          </AcademicField>
        </div>
        <p className="academic-hint">
          O código segue o padrão institucional EST + sigla + número. Cada código é único no
          período. O acesso é limitado aos seus vínculos acadêmicos.
        </p>
        <div className="academic-actions">
          <button className="primary" disabled={busy}>
            {busy ? 'Salvando…' : selected ? 'Salvar turma' : 'Cadastrar turma'}
          </button>
          {selected && (
            <button type="button" className="secondary" onClick={reset}>
              Nova turma
            </button>
          )}
        </div>
      </form>
      {selected && (
        <div className="academic-box">
          <h3>Acesso e situação da turma</h3>
          <p>
            {selected.ativa_turma ? 'Turma ativa' : 'Turma inativa'} ·{' '}
            {selected.autoinscricao_ativa_turma
              ? 'Autoinscrição habilitada'
              : 'Autoinscrição desabilitada'}
          </p>
          {accessCode && (
            <>
              <p className="academic-hint">
                Guarde o código agora. Por segurança, ele não será exibido novamente ao recarregar.
              </p>
              <code>{accessCode}</code>
              <button
                className="secondary"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(accessCode);
                    setSuccess('Código copiado!');
                  } catch {
                    setMessage('Não foi possível copiar. Selecione o código e copie manualmente.');
                  }
                }}
              >
                Copiar código de acesso
              </button>
            </>
          )}
          <div className="academic-actions">
            <button
              className="secondary"
              disabled={busy || !selected.ativa_turma}
              onClick={() => action('codigo')}
            >
              Gerar novo código de acesso
            </button>
            <button
              className="secondary"
              disabled={busy || !selected.ativa_turma}
              onClick={() => action('autoinscricao')}
            >
              {selected.autoinscricao_ativa_turma ? 'Desabilitar' : 'Habilitar'} autoinscrição
            </button>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => (selected.ativa_turma ? setConfirm(true) : action('reativar'))}
            >
              {selected.ativa_turma ? 'Inativar turma' : 'Reativar turma'}
            </button>
          </div>
        </div>
      )}
      <div className="field">
        <label htmlFor="filtro-turmas">Situação das turmas</label>
        <select
          id="filtro-turmas"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="true">Ativas</option>
          <option value="false">Inativas</option>
          <option value="">Todas</option>
        </select>
      </div>
      {loading ? (
        <p aria-live="polite">Carregando turmas…</p>
      ) : !items.length ? (
        <p className="academic-empty">Nenhuma turma disponível para seu vínculo e filtro.</p>
      ) : (
        <div className="academic-list">
          {items.map((item) => (
            <article className="academic-box" key={item.id_turma}>
              <h3>
                {item.codigo_turma} · {item.periodo_letivo}
              </h3>
              <p className="academic-meta">
                TCC {item.nivel_turma} · {item.ativa_turma ? 'Ativa' : 'Inativa'} ·{' '}
                {courses.find((c) => c.id_curso === item.id_curso)?.nome_curso ||
                  'Curso cadastrado'}
              </p>
              <button className="secondary" onClick={() => open(item.id_turma)} disabled={busy}>
                Gerenciar {item.codigo_turma}
              </button>
            </article>
          ))}
        </div>
      )}
      <Pager page={page} pages={pages} onChange={setPage} />
      {confirm && (
        <ConfirmDialog title="Inativar turma?" onClose={() => setConfirm(false)}>
          <p>A turma deixará de aceitar inscrições. O histórico será preservado.</p>
          <div className="academic-actions">
            <button className="secondary" onClick={() => setConfirm(false)} disabled={busy}>
              Cancelar
            </button>
            <button className="primary" onClick={() => action('inativar')} disabled={busy}>
              Confirmar inativação da turma
            </button>
          </div>
        </ConfirmDialog>
      )}
    </section>
  );
}
