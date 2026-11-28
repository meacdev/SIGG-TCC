import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { api, ApiError } from './api';
import { Notice } from './components';
import {
  AcademicField,
  ConfirmDialog,
  failure,
  fieldProps,
  Pager,
  sessionError,
  type SessionProps,
} from './academic';
import {
  BLOCKER_LABELS,
  COURSE_PROFILES,
  isCourseProfile,
  INSTITUTIONAL_DOMAIN,
  KIND_LABELS,
  MANAGED_PROFILES,
  PROFILE_LABELS,
  SITUATION_LABELS,
  emptyUser,
  endOfDay,
  formatDate,
  formatDay,
  profileLabel,
  userPayload,
  validateUser,
  valuesFrom,
  type Blocker,
  type Kind,
  type ManagedProfile,
  type ManagedUser,
  type Situation,
  type UserErrors,
  type UserValues,
} from './admin-users';
import type { Course, User } from './types';
import './users.css';

const BASE = '/admin/usuarios';
type Result = { body: { data: ManagedUser; code?: string; message?: string }; etag: string | null };
type Feedback = { text: string; success: boolean };

function send(path: string, method: string, body: object, etag?: string) {
  return api.request<ManagedUser>(
    `${BASE}${path}`,
    { method, headers: etag ? { 'If-Match': etag } : {}, body: JSON.stringify(body) },
    true,
  ) as Promise<Result>;
}
const conflict = (error: unknown) =>
  error instanceof ApiError && (error.code === 'UC_14_M14' || [412, 428].includes(error.status));

/** UC14 Manter Usuários: tela exclusiva do Administrador (secretaria). */
export function Users({ onSessionEnded, user: me }: SessionProps & { user: User | null }) {
  const [items, setItems] = useState<ManagedUser[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [filters, setFilters] = useState({
    busca: '',
    situacao: '',
    tipo_cadastro: '',
    perfil: '',
    id_curso: '',
  });
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [selected, setSelected] = useState<ManagedUser | null>(null);
  const [etag, setEtag] = useState('');
  const [creating, setCreating] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [stale, setStale] = useState(false);
  const [busy, setBusy] = useState(false);
  const detail = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    let active = true;
    api
      .courses()
      .then((data) => {
        if (active) setCourses(data);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setListError('');
    const query = new URLSearchParams({ page: String(page), per_page: '20' });
    for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
    api
      .request<ManagedUser[]>(`${BASE}?${query}`, {}, true)
      .then((result) => {
        if (!active) return;
        setItems(result.body.data);
        setPages(result.body.meta?.pages || 1);
        setTotal((result.body.meta as { total?: number } | undefined)?.total ?? 0);
      })
      .catch((error) => {
        if (!active) return;
        sessionError(error, onSessionEnded);
        setListError(failure(error));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [page, filters, attempt]);

  useEffect(() => {
    if (selected || creating) detail.current?.focus();
  }, [selected?.id_usuario, creating]);

  function filter(name: keyof typeof filters, value: string) {
    setFilters((previous) => ({ ...previous, [name]: value }));
    setPage(1);
  }
  function report(error: unknown) {
    sessionError(error, onSessionEnded);
    setFeedback({ text: failure(error), success: false });
    setStale(conflict(error));
  }
  /** Atualiza o usuário aberto com a resposta e a nova versão (ETag) do servidor. */
  function applied(result: Result, success = true) {
    const data = result.body.data;
    const change = data.alteracao_email;
    let text = result.body.message || '';
    if (change?.enviado)
      text += ` Enviamos o link de confirmação para ${change.novo_email}. O e-mail atual continua valendo até a confirmação.`;
    else if (change)
      text += ` Não foi possível enviar a confirmação para ${change.novo_email}. Salve o e-mail novamente para reenviar.`;
    setSelected(data);
    setEtag(result.etag || '');
    setStale(false);
    setFeedback(text ? { text: text.trim(), success: success && change?.enviado !== false } : null);
    setAttempt((value) => value + 1);
  }
  async function open(id: number) {
    setBusy(true);
    setCreating(false);
    setFeedback(null);
    setStale(false);
    try {
      const result = await api.request<ManagedUser>(`${BASE}/${id}`, {}, true);
      setSelected(result.body.data);
      setEtag(result.etag || '');
    } catch (error) {
      report(error);
    } finally {
      setBusy(false);
    }
  }
  function close() {
    setSelected(null);
    setEtag('');
    setCreating(false);
    setFeedback(null);
    setStale(false);
  }
  async function act(path: string, method: string, body: object) {
    if (!selected || busy) return false;
    setBusy(true);
    setFeedback(null);
    try {
      applied(await send(`/${selected.id_usuario}${path}`, method, body, etag));
      return true;
    } catch (error) {
      report(error);
      throw error;
    } finally {
      setBusy(false);
    }
  }

  const self = !!me && selected?.id_usuario === me.id_usuario;
  return (
    <section className="users-page">
      <div className="page-intro">
        <span className="eyebrow">GESTÃO DE ACESSOS</span>
        <h1>Usuários</h1>
        <p>
          Pré-cadastre estudantes e docentes, mantenha os dados das contas e defina quem coordena ou
          ministra a disciplina de TCC em cada curso.
        </p>
      </div>
      <div className="academic-actions users-toolbar">
        <button
          className="primary"
          type="button"
          onClick={() => {
            close();
            setCreating(true);
          }}
          disabled={busy}
        >
          Pré-cadastrar usuário
        </button>
      </div>
      {feedback && (
        <Notice message={feedback.text} success={feedback.success}>
          {stale && selected && (
            <button className="text-button" type="button" onClick={() => open(selected.id_usuario)}>
              Recarregar usuário
            </button>
          )}
        </Notice>
      )}
      {creating && (
        <div className="academic-box">
          <h2 ref={detail} tabIndex={-1}>
            Pré-cadastro de usuário
          </h2>
          <UserForm
            courses={courses}
            busy={busy}
            onSubmit={async (body) => {
              setBusy(true);
              setFeedback(null);
              try {
                const result = await send('', 'POST', body);
                setCreating(false);
                applied(result, result.body.code !== 'UC_14_CONVITE_PENDENTE');
              } catch (error) {
                report(error);
                throw error;
              } finally {
                setBusy(false);
              }
            }}
            onCancel={close}
          />
        </div>
      )}
      {selected && (
        <UserDetail
          key={`${selected.id_usuario}-${etag}`}
          user={selected}
          self={self}
          courses={courses}
          busy={busy || stale}
          heading={detail}
          onAct={act}
          onClose={close}
        />
      )}
      <form
        className="academic-box users-filters"
        role="search"
        aria-label="Buscar usuários"
        onSubmit={(event) => {
          event.preventDefault();
          filter('busca', search.trim());
        }}
      >
        <h2>Usuários cadastrados</h2>
        <div className="users-filter-grid">
          <div className="field users-search">
            <label htmlFor="busca-usuarios">Nome, e-mail ou matrícula</label>
            <div className="users-search-row">
              <input
                id="busca-usuarios"
                type="search"
                maxLength={100}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <button className="secondary">Buscar</button>
            </div>
          </div>
          <FilterSelect
            id="filtro-situacao"
            label="Situação"
            value={filters.situacao}
            onChange={(value) => filter('situacao', value)}
            options={SITUATION_LABELS}
          />
          <FilterSelect
            id="filtro-tipo"
            label="Tipo de cadastro"
            value={filters.tipo_cadastro}
            onChange={(value) => filter('tipo_cadastro', value)}
            options={KIND_LABELS}
          />
          <FilterSelect
            id="filtro-perfil"
            label="Perfil de acesso"
            value={filters.perfil}
            onChange={(value) => filter('perfil', value)}
            options={PROFILE_LABELS}
          />
          <FilterSelect
            id="filtro-curso"
            label="Curso"
            value={filters.id_curso}
            onChange={(value) => filter('id_curso', value)}
            options={Object.fromEntries(courses.map((c) => [c.id_curso, c.nome_curso]))}
          />
        </div>
      </form>
      {listError ? (
        <Notice message={listError}>
          <button className="text-button" type="button" onClick={() => setAttempt((v) => v + 1)}>
            Tentar novamente
          </button>
        </Notice>
      ) : loading ? (
        <p aria-live="polite">Carregando usuários…</p>
      ) : !items.length ? (
        <p className="academic-empty" role="status">
          Nenhum usuário encontrado para os filtros informados.
        </p>
      ) : (
        <div className="monitoring-table academic-table-wrap">
          <table className="academic-table users-table">
            <caption>{total} usuário(s) encontrado(s)</caption>
            <thead>
              <tr>
                <th scope="col">Usuário</th>
                <th scope="col">Tipo</th>
                <th scope="col">Perfis</th>
                <th scope="col">Situação</th>
                <th scope="col">
                  <span className="sr-only">Ações</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id_usuario}
                  aria-current={selected?.id_usuario === item.id_usuario ? 'true' : undefined}
                >
                  <td>
                    <strong>{item.nome_usuario}</strong>
                    <span className="monitoring-registration">{item.email_usuario}</span>
                  </td>
                  <td>{KIND_LABELS[item.tipo_cadastro]}</td>
                  <td>{item.perfis.map(profileLabel).join(', ') || '—'}</td>
                  <td>
                    <StatusTag situation={item.situacao_conta} />
                  </td>
                  <td>
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => open(item.id_usuario)}
                      disabled={busy}
                      aria-label={`Gerenciar ${item.nome_usuario}`}
                    >
                      Gerenciar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pager page={page} pages={pages} onChange={setPage} />
    </section>
  );
}

function FilterSelect({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: Record<string, string>;
  onChange: (value: string) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Todos</option>
        {Object.entries(options).map(([key, text]) => (
          <option key={key} value={key}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
}

function StatusTag({ situation }: { situation: Situation }) {
  return <span className={`user-status ${situation}`}>{SITUATION_LABELS[situation]}</span>;
}

/** Formulário compartilhado entre o pré-cadastro e a alteração de dados. */
function UserForm({
  original,
  courses,
  busy,
  onSubmit,
  onCancel,
}: {
  original?: ManagedUser;
  courses: Course[];
  busy: boolean;
  onSubmit: (body: Record<string, unknown>) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<UserValues>(() =>
    original ? valuesFrom(original) : { ...emptyUser },
  );
  const [errors, setErrors] = useState<UserErrors>({});
  const [message, setMessage] = useState('');
  const prefix = original ? 'editar' : 'novo';
  const kind = values.tipo_cadastro;
  const emailChanged =
    !!original && values.email_usuario.trim().toLowerCase() !== original.email_usuario;

  function update(name: keyof UserValues, value: string) {
    setValues((previous) => ({ ...previous, [name]: value }));
    setErrors((previous) => ({ ...previous, [name]: undefined }));
  }
  const input = (name: keyof UserValues) => ({
    id: `${prefix}-${name}`,
    'aria-invalid': !!errors[name],
    'aria-describedby': errors[name] ? `${prefix}-${name}-error` : undefined,
    value: values[name],
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      update(name, event.target.value),
    disabled: busy,
  });
  const field = (name: keyof UserValues, label: string, children: ReactNode, optional = false) => (
    <AcademicField
      name={`${prefix}-${name}`}
      label={optional ? `${label} (opcional)` : label}
      error={errors[name]}
    >
      {children}
    </AcademicField>
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const issues = validateUser(values, original);
    setErrors(issues);
    if (Object.keys(issues).length) {
      setMessage('Preencha os campos obrigatórios e confira o formato dos campos destacados.');
      document.getElementById(`${prefix}-${Object.keys(issues)[0]}`)?.focus();
      return;
    }
    const body = userPayload(values, original);
    if (original && !Object.keys(body).length) {
      setMessage('Nenhuma alteração para salvar.');
      return;
    }
    setMessage('');
    try {
      await onSubmit(body);
    } catch (error) {
      if (error instanceof ApiError) setErrors(error.fields as UserErrors);
    }
  }

  return (
    <form onSubmit={submit} noValidate aria-label={original ? 'Dados do usuário' : 'Pré-cadastro'}>
      {message && <Notice message={message} />}
      {!original && (
        <fieldset className="users-kind" disabled={busy}>
          <legend>Tipo de cadastro</legend>
          {(['estudante', 'docente', 'administrativo'] as Kind[]).map((option) => (
            <label key={option} className={kind === option ? 'selected' : ''}>
              <input
                type="radio"
                name="novo-tipo_cadastro"
                value={option}
                checked={kind === option}
                onChange={() => {
                  setValues({ ...values, tipo_cadastro: option });
                  setErrors({});
                  setMessage('');
                }}
              />
              {KIND_LABELS[option]}
            </label>
          ))}
        </fieldset>
      )}
      <div className="academic-grid">
        <div className="users-full">
          {field(
            'nome_usuario',
            'Nome completo',
            <input {...input('nome_usuario')} autoComplete="off" maxLength={100} required />,
          )}
        </div>
        <div className="users-full">
          {field(
            'email_usuario',
            'E-mail',
            <input
              {...input('email_usuario')}
              type="email"
              autoComplete="off"
              maxLength={254}
              placeholder={
                kind === 'docente' && values.tipo_professor === 'externo'
                  ? 'nome@instituicao.br'
                  : `nome@${INSTITUTIONAL_DOMAIN}`
              }
              required
            />,
          )}
          <p className="academic-hint">
            {emailChanged
              ? 'O novo e-mail só passa a valer depois que o usuário confirmar pelo link enviado.'
              : kind === 'docente' && values.tipo_professor === 'externo'
                ? 'Docentes externos podem usar o e-mail da instituição de origem.'
                : original
                  ? `Ao alterar, use o e-mail institucional @${INSTITUTIONAL_DOMAIN}.`
                  : `Use o e-mail institucional @${INSTITUTIONAL_DOMAIN}.`}
          </p>
        </div>
        {field(
          'cpf_usuario',
          'CPF',
          <input
            {...input('cpf_usuario')}
            inputMode="numeric"
            autoComplete="off"
            placeholder="000.000.000-00"
            maxLength={14}
          />,
          true,
        )}
        {field(
          'telefone_usuario',
          'Telefone',
          <input
            {...input('telefone_usuario')}
            type="tel"
            autoComplete="off"
            placeholder="(92) 99999-9999"
            maxLength={30}
          />,
          true,
        )}
        {kind === 'estudante' && (
          <>
            {field(
              'matricula_estudante',
              'Matrícula',
              <input
                {...input('matricula_estudante')}
                autoComplete="off"
                maxLength={30}
                required
              />,
            )}
            {field(
              'id_curso',
              'Curso',
              <select {...input('id_curso')} disabled={busy || !courses.length} required>
                <option value="">{courses.length ? 'Selecione' : 'Carregando cursos…'}</option>
                {courses.map((course) => (
                  <option key={course.id_curso} value={course.id_curso}>
                    {course.nome_curso}
                  </option>
                ))}
              </select>,
            )}
          </>
        )}
        {kind === 'docente' && (
          <>
            {field(
              'tipo_professor',
              'Vínculo institucional',
              <select {...input('tipo_professor')}>
                <option value="interno">Professor interno · UEA</option>
                <option value="externo">Professor / avaliador externo</option>
              </select>,
            )}
            {field(
              'titulacao_professor',
              'Titulação',
              <select {...input('titulacao_professor')} required>
                <option value="">Selecione</option>
                <option value="Especialista">Especialista</option>
                <option value="Mestre">Mestre</option>
                <option value="Doutor">Doutor</option>
              </select>,
            )}
            <div className="users-full">
              {field(
                'instituicao_origem_professor',
                'Instituição de origem',
                <input
                  {...input('instituicao_origem_professor')}
                  autoComplete="off"
                  maxLength={200}
                />,
                values.tipo_professor !== 'externo',
              )}
            </div>
          </>
        )}
      </div>
      {!original && (
        <p className="academic-hint">
          A conta fica pendente até o usuário definir a senha pelo convite enviado por e-mail.
          {kind === 'administrativo' &&
            ' Depois de ativa, conceda o perfil de administrador na seção de perfis.'}
        </p>
      )}
      <div className="academic-actions">
        <button className="primary" disabled={busy}>
          {busy ? 'Salvando…' : original ? 'Salvar dados' : 'Pré-cadastrar e enviar convite'}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => {
            if (original) {
              setValues(valuesFrom(original));
              setErrors({});
              setMessage('');
            } else onCancel();
          }}
        >
          {original ? 'Descartar alterações' : 'Cancelar'}
        </button>
      </div>
    </form>
  );
}

type Act = (path: string, method: string, body: object) => Promise<boolean>;

function UserDetail({
  user,
  self,
  courses,
  busy,
  heading,
  onAct,
  onClose,
}: {
  user: ManagedUser;
  self: boolean;
  courses: Course[];
  busy: boolean;
  heading: React.RefObject<HTMLHeadingElement | null>;
  onAct: Act;
  onClose: () => void;
}) {
  return (
    <>
      <div className="academic-box users-detail">
        <h2 ref={heading} tabIndex={-1}>
          {user.nome_usuario}
          <StatusTag situation={user.situacao_conta} />
        </h2>
        <p className="academic-meta">
          <span>Cadastro #{user.id_usuario}</span>
          <span>{KIND_LABELS[user.tipo_cadastro]}</span>
          <span>Criado em {formatDate(user.data_criacao_usuario)}</span>
          <span>Atualizado em {formatDate(user.data_atualizacao_usuario, true)}</span>
        </p>
        <h3>Dados cadastrais</h3>
        <UserForm
          original={user}
          courses={courses}
          busy={busy}
          onSubmit={(body) => onAct('', 'PATCH', body)}
          onCancel={onClose}
        />
      </div>
      <AccountStatus user={user} self={self} busy={busy} onAct={onAct} />
      <Profiles user={user} self={self} courses={courses} busy={busy} onAct={onAct} />
      <div className="academic-actions">
        <button type="button" className="secondary" onClick={onClose}>
          Fechar usuário
        </button>
      </div>
    </>
  );
}

function AccountStatus({
  user,
  self,
  busy,
  onAct,
}: {
  user: ManagedUser;
  self: boolean;
  busy: boolean;
  onAct: Act;
}) {
  const [changing, setChanging] = useState(false);
  const [blockers, setBlockers] = useState<Blocker[]>([]);
  const pending = user.situacao_conta === 'pendente';
  return (
    <div className="academic-box">
      <h2>Situação da conta</h2>
      <p>
        {user.ativo_usuario
          ? pending
            ? `Aguardando o usuário definir a senha. Convite válido até ${formatDate(user.data_expiracao_convite, true) || 'expirar'}.`
            : 'Conta ativa. O usuário entra com e-mail e senha.'
          : 'Conta inativa. O usuário não consegue entrar e as sessões foram encerradas.'}
      </p>
      {blockers.length > 0 && (
        <div className="inline-warning" role="alert">
          <p>Transfira estes vínculos antes de inativar:</p>
          <ul>
            {blockers.map((item) => (
              <li key={`${item.tipo}-${item.id}`}>
                {BLOCKER_LABELS[item.tipo]} ·{' '}
                {item.tipo === 'banca' ? formatDate(item.descricao, true) : item.descricao}
              </li>
            ))}
          </ul>
        </div>
      )}
      {self && user.ativo_usuario && (
        <p className="academic-hint">Você não pode inativar a própria conta.</p>
      )}
      <div className="academic-actions">
        {pending && (
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => onAct('/convite', 'POST', {}).catch(() => undefined)}
          >
            Reenviar convite
          </button>
        )}
        <button
          type="button"
          className={user.ativo_usuario ? 'danger-outline' : 'secondary'}
          disabled={busy || (self && user.ativo_usuario)}
          onClick={() => setChanging(true)}
        >
          {user.ativo_usuario ? 'Inativar conta' : 'Reativar conta'}
        </button>
      </div>
      {changing && (
        <ReasonDialog
          title={user.ativo_usuario ? 'Inativar conta?' : 'Reativar conta?'}
          description={
            user.ativo_usuario
              ? 'O usuário perde o acesso e as sessões abertas são encerradas. O histórico acadêmico é preservado.'
              : 'O usuário volta a poder entrar no SIGG-TCC com os perfis que já possui.'
          }
          confirm={user.ativo_usuario ? 'Confirmar inativação' : 'Confirmar reativação'}
          danger={user.ativo_usuario}
          busy={busy}
          onClose={() => setChanging(false)}
          onConfirm={async (justificativa) => {
            setBlockers([]);
            try {
              await onAct('/situacao', 'PATCH', {
                ativo_usuario: !user.ativo_usuario,
                justificativa,
              });
            } catch (error) {
              const found = (error as ApiError).fields?.vinculos as unknown;
              if (Array.isArray(found)) setBlockers(found as Blocker[]);
              throw error;
            }
          }}
        />
      )}
    </div>
  );
}

type Revocation = {
  codigo_perfil: ManagedProfile;
  id_curso?: number;
  label: string;
  detail?: string;
};
const GRANT_FIELDS: Record<string, string> = {
  id_curso: 'perfil-curso',
  departamento_unidade: 'perfil-departamento',
  data_expiracao: 'perfil-expiracao',
};

function Profiles({
  user,
  self,
  courses,
  busy,
  onAct,
}: {
  user: ManagedUser;
  self: boolean;
  courses: Course[];
  busy: boolean;
  onAct: Act;
}) {
  const internal = user.professor?.tipo_professor === 'interno' && user.ativo_usuario;
  const options = MANAGED_PROFILES.filter((code) =>
    isCourseProfile(code) ? internal : user.ativo_usuario,
  );
  const empty = {
    codigo_perfil: (options[0] || '') as ManagedProfile | '',
    id_curso: '',
    departamento_unidade: '',
    data: '',
  };
  const [values, setValues] = useState(empty);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [granting, setGranting] = useState(false);
  const [revoking, setRevoking] = useState<Revocation | null>(null);
  const code = values.codigo_perfil as ManagedProfile | '';
  const byCourse = !!code && isCourseProfile(code);

  const revocations: Revocation[] = [];
  for (const link of user.vinculos_curso)
    for (const profile of COURSE_PROFILES)
      if (link[profile] && user.perfis.includes(profile))
        revocations.push({
          codigo_perfil: profile,
          id_curso: link.id_curso,
          label: `${profileLabel(profile)} · ${link.nome_curso}`,
          detail: [link.departamento_unidade, `Vínculo desde ${formatDay(link.data_inicio)}`]
            .filter(Boolean)
            .join(' · '),
        });
  if (user.perfis.includes('administrador'))
    revocations.push({ codigo_perfil: 'administrador', label: profileLabel('administrador') });
  const derived = user.perfis.filter(
    (profile) => !MANAGED_PROFILES.includes(profile as ManagedProfile),
  );
  const grant = (profile: string) => user.concessoes.find((item) => item.codigo_perfil === profile);

  function review(event: FormEvent) {
    event.preventDefault();
    const issues: Record<string, string> = {};
    if (!code) issues['perfil-codigo'] = 'Obrigatório.';
    if (byCourse && !values.id_curso) issues['perfil-curso'] = 'Obrigatório.';
    if (code === 'coordenador' && !values.departamento_unidade.trim())
      issues['perfil-departamento'] = 'Obrigatório para coordenador.';
    if (values.data && new Date(endOfDay(values.data)!) <= new Date())
      issues['perfil-expiracao'] = 'Informe uma data futura.';
    setErrors(issues);
    if (!Object.keys(issues).length) setGranting(true);
  }

  return (
    <div className="academic-box">
      <h2>Perfis de acesso</h2>
      {user.perfis.length ? (
        <ul className="users-profiles">
          {revocations.map((item) => {
            const current = grant(item.codigo_perfil);
            const blocked = self && item.codigo_perfil === 'administrador';
            return (
              <li key={`${item.codigo_perfil}-${item.id_curso || ''}`}>
                <span>
                  <strong>{item.label}</strong>
                  {current?.data_expiracao && (
                    <small>Expira em {formatDate(current.data_expiracao, true)}</small>
                  )}
                  {item.detail && <small>{item.detail}</small>}
                </span>
                <button
                  type="button"
                  className="danger-outline"
                  disabled={busy || blocked}
                  title={
                    blocked ? 'Você não pode remover o próprio perfil de administrador.' : undefined
                  }
                  onClick={() => setRevoking(item)}
                  aria-label={`Revogar ${item.label}`}
                >
                  Revogar
                </button>
              </li>
            );
          })}
          {derived.map((profile) => (
            <li key={profile}>
              <span>
                <strong>{profileLabel(profile)}</strong>
                <small>Atribuído pelos fluxos acadêmicos; não é alterado aqui.</small>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="academic-empty">Nenhum perfil de acesso concedido.</p>
      )}
      {options.length ? (
        <form className="users-grant" onSubmit={review} noValidate aria-label="Conceder perfil">
          <h3>Conceder perfil</h3>
          <div className="academic-grid">
            <AcademicField name="perfil-codigo" label="Perfil" error={errors['perfil-codigo']}>
              <select
                id="perfil-codigo"
                value={values.codigo_perfil}
                onChange={(event) =>
                  setValues({
                    ...values,
                    codigo_perfil: event.target.value as ManagedProfile,
                    data: '',
                  })
                }
                disabled={busy}
              >
                {options.map((option) => (
                  <option key={option} value={option}>
                    {profileLabel(option)}
                  </option>
                ))}
              </select>
            </AcademicField>
            {byCourse && (
              <AcademicField name="perfil-curso" label="Curso" error={errors['perfil-curso']}>
                <select
                  id="perfil-curso"
                  aria-invalid={!!errors['perfil-curso']}
                  value={values.id_curso}
                  onChange={(event) => setValues({ ...values, id_curso: event.target.value })}
                  disabled={busy}
                >
                  <option value="">Selecione</option>
                  {courses.map((course) => (
                    <option key={course.id_curso} value={course.id_curso}>
                      {course.nome_curso}
                    </option>
                  ))}
                </select>
              </AcademicField>
            )}
            {code === 'coordenador' && (
              <AcademicField
                name="perfil-departamento"
                label="Departamento / unidade"
                error={errors['perfil-departamento']}
              >
                <input
                  {...fieldProps('perfil-departamento', errors)}
                  maxLength={200}
                  value={values.departamento_unidade}
                  onChange={(event) =>
                    setValues({ ...values, departamento_unidade: event.target.value })
                  }
                  disabled={busy}
                />
              </AcademicField>
            )}
            {code !== 'administrador' && (
              <AcademicField
                name="perfil-expiracao"
                label="Válido até (opcional)"
                error={errors['perfil-expiracao']}
              >
                <input
                  {...fieldProps('perfil-expiracao', errors)}
                  type="date"
                  value={values.data}
                  onChange={(event) => setValues({ ...values, data: event.target.value })}
                  disabled={busy}
                />
              </AcademicField>
            )}
          </div>
          <p className="academic-hint">
            {byCourse
              ? 'Professor da disciplina e coordenador valem por curso e exigem docente interno ativo.'
              : 'O perfil de administrador não expira e dá acesso a esta tela.'}{' '}
            Sem data, o perfil vale até ser revogado.
          </p>
          <div className="academic-actions">
            <button className="primary" disabled={busy}>
              Conceder perfil
            </button>
          </div>
        </form>
      ) : (
        <p className="academic-hint">
          {user.ativo_usuario
            ? 'Este usuário não pode receber perfis de gestão.'
            : 'Reative a conta para conceder perfis.'}
        </p>
      )}
      {granting && code && (
        <ReasonDialog
          title={`Conceder ${profileLabel(code)}?`}
          description={
            byCourse
              ? `O usuário passa a ter este perfil no curso ${courses.find((c) => String(c.id_curso) === values.id_curso)?.nome_curso || 'selecionado'}.`
              : 'O usuário passa a gerenciar contas e perfis no SIGG-TCC.'
          }
          confirm="Confirmar concessão"
          busy={busy}
          onClose={() => setGranting(false)}
          onConfirm={async (justificativa) => {
            const body: Record<string, unknown> = { codigo_perfil: code, justificativa };
            if (byCourse) body.id_curso = Number(values.id_curso);
            if (code === 'coordenador')
              body.departamento_unidade = values.departamento_unidade.trim();
            if (values.data && code !== 'administrador')
              body.data_expiracao = endOfDay(values.data);
            try {
              await onAct('/perfis', 'POST', body);
            } catch (error) {
              if (error instanceof ApiError)
                setErrors(
                  Object.fromEntries(
                    Object.entries(error.fields).map(([key, text]) => [
                      GRANT_FIELDS[key] || 'perfil-codigo',
                      String(text),
                    ]),
                  ),
                );
              throw error;
            }
          }}
        />
      )}
      {revoking && (
        <ReasonDialog
          title={`Revogar ${revoking.label}?`}
          description="O usuário perde as permissões deste perfil imediatamente. O histórico de concessões é preservado."
          confirm="Confirmar revogação"
          danger
          busy={busy}
          onClose={() => setRevoking(null)}
          onConfirm={(justificativa) =>
            onAct('/perfis/revogar', 'POST', {
              codigo_perfil: revoking.codigo_perfil,
              ...(revoking.id_curso ? { id_curso: revoking.id_curso } : {}),
              justificativa,
            })
          }
        />
      )}
    </div>
  );
}

/** Operações sensíveis pedem justificativa, registrada na auditoria (RN 08). */
function ReasonDialog({
  title,
  description,
  confirm,
  danger = false,
  busy,
  onClose,
  onConfirm,
}: {
  title: string;
  description: string;
  confirm: string;
  danger?: boolean;
  busy: boolean;
  onClose: () => void;
  onConfirm: (justificativa: string) => Promise<unknown>;
}) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!reason.trim()) {
      setError('Informe a justificativa da operação.');
      return;
    }
    setError('');
    setMessage('');
    try {
      await onConfirm(reason.trim());
      onClose();
    } catch (failed) {
      setMessage(failure(failed));
    }
  }
  return (
    <ConfirmDialog title={title} onClose={() => !busy && onClose()}>
      <p>{description}</p>
      {message && <Notice message={message} />}
      <form onSubmit={submit} noValidate>
        <AcademicField name="justificativa" label="Justificativa" error={error}>
          <textarea
            id="justificativa"
            aria-invalid={!!error}
            aria-describedby={error ? 'justificativa-error' : undefined}
            maxLength={1000}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled={busy}
            required
          />
        </AcademicField>
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            Cancelar
          </button>
          <button className={danger ? 'danger' : 'primary'} disabled={busy}>
            {busy ? 'Aguarde…' : confirm}
          </button>
        </div>
      </form>
    </ConfirmDialog>
  );
}
