import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Field, Icon, Notice, Password, inputA11y } from './components';
import type { Course, FieldErrors, FormValues, User } from './types';
import { emptyForm, fromUser, payload, validEmail, validate } from './validation';
import { Classes } from './classes';
import { Enrollments } from './enrollments';
import { Works } from './works';
import { Meetings } from './meetings';
import { Monitoring } from './monitoring';
import './academic.css';

type Page =
  | 'cadastro'
  | 'entrar'
  | 'perfil'
  | 'turmas'
  | 'matriculas'
  | 'trabalhos'
  | 'reunioes'
  | 'monitoramento';
const currentPage = (): Page => {
  const page = window.location.hash.replace('#/', '');
  return [
    'entrar',
    'perfil',
    'turmas',
    'matriculas',
    'trabalhos',
    'reunioes',
    'monitoramento',
  ].includes(page)
    ? (page as Page)
    : 'cadastro';
};
const navigate = (page: Page) => {
  window.location.hash = `/${page}`;
};

function errorDetails(error: unknown): { message: string; fields: FieldErrors } {
  if (!(error instanceof ApiError))
    return { message: 'Não foi possível concluir a operação. Tente novamente.', fields: {} };
  const fields: FieldErrors = { ...error.fields };
  if (['UC_01_M03', 'UC_01_M04'].includes(error.code)) fields.email_usuario = error.message;
  if (error.code === 'SENHA_INVALIDA') fields.senha = error.message;
  if (error.code === 'URL_INVALIDA') fields.url_lattes_docente = error.message;
  if (error.code === 'MATRICULA_DUPLICADA') fields.matricula_aluno = error.message;
  if (error.code === 'CURSO_INVALIDO') fields.id_curso = error.message;
  return { message: error.message, fields };
}

export function App() {
  const [page, setPage] = useState<Page>(currentPage);
  const [notice, setNotice] = useState('');
  const [email, setEmail] = useState('');
  const protectedPage = [
    'perfil',
    'turmas',
    'matriculas',
    'trabalhos',
    'reunioes',
    'monitoramento',
  ].includes(page);
  useEffect(() => {
    const change = () => {
      setPage(currentPage());
      setNotice('');
    };
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  useEffect(() => {
    const titles = {
      cadastro: 'Crie sua conta',
      entrar: 'Entrar',
      perfil: 'Meu cadastro',
      turmas: 'Turmas',
      matriculas: 'Matrículas',
      trabalhos: 'Trabalhos',
      reunioes: 'Reuniões',
      monitoramento: 'Monitorar Prazos',
    };
    document.title = `${titles[page]} · SIGG-TCC`;
    window.scrollTo(0, 0);
    if (protectedPage && !api.hasSession()) {
      navigate('entrar');
    }
  }, [page]);

  function sessionEnded(message: string) {
    api.clearSession();
    setPage('entrar');
    // Replace the hash without triggering the listener that clears the feedback.
    window.history.replaceState(null, '', '#/entrar');
    setNotice(message);
  }

  async function logout() {
    try {
      await api.logout();
      sessionEnded('Você saiu da sua conta.');
    } catch {
      sessionEnded(
        'Você saiu deste navegador. Não foi possível encerrar a sessão no servidor; ela expirará por inatividade.',
      );
    }
  }

  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById('main-content')?.focus();
        }}
      >
        Ir para o conteúdo
      </a>
      <aside className="brand-panel" aria-label="Sobre o SIGG-TCC">
        <a className="brand" href="#/cadastro" aria-label="SIGG-TCC, cadastro">
          <span className="brand-symbol">
            <Icon name="cap" size={30} />
          </span>
          <span>
            SIGG<span className="brand-dash">-</span>TCC<small>GESTÃO E GOVERNANÇA</small>
          </span>
        </a>
        <div className="brand-content">
          <span className="eyebrow light">NUCOMP · UNIVERSIDADE DO ESTADO DO AMAZONAS</span>
          <h1>
            Grandes ideias.
            <br />
            Uma jornada
            <br />
            <em>compartilhada.</em>
          </h1>
          <p>
            Um ponto de encontro para estudantes e docentes em cada etapa do trabalho de conclusão
            de curso.
          </p>
          <div className="journey" aria-label="Etapas da jornada acadêmica">
            <div>
              <span className="journey-dot">
                <Icon name="book" size={18} />
              </span>
              <p>
                <strong>Do primeiro tema à defesa</strong>
                <small>Seu percurso acadêmico em um só lugar.</small>
              </p>
            </div>
            <div>
              <span className="journey-dot">
                <Icon name="user" size={18} />
              </span>
              <p>
                <strong>Conhecimento que conecta</strong>
                <small>Estudantes, orientadores e avaliadores.</small>
              </p>
            </div>
            <div>
              <span className="journey-dot">
                <Icon name="shield" size={18} />
              </span>
              <p>
                <strong>Cada etapa com seu registro</strong>
                <small>Mais organização para seguir em frente.</small>
              </p>
            </div>
          </div>
        </div>
        <div className="institution">
          <span className="uea-wordmark">
            UEA
            <span>
              UNIVERSIDADE DO
              <br />
              ESTADO DO AMAZONAS
            </span>
          </span>
          <span className="institution-unit">
            NUCOMP<small>Núcleo de Computação</small>
          </span>
        </div>
        <span className="panel-grid" aria-hidden="true" />
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            Portal acadêmico <span className="topbar-divider">/</span>{' '}
            {protectedPage ? 'Área acadêmica' : 'Acesso'}
          </span>
          {protectedPage ? (
            <button className="text-button" onClick={logout}>
              Sair da conta <Icon name="arrow" size={16} />
            </button>
          ) : (
            <span>
              {page === 'cadastro' ? 'Já tem uma conta?' : 'Ainda não tem conta?'}{' '}
              <a href={page === 'cadastro' ? '#/entrar' : '#/cadastro'}>
                {page === 'cadastro' ? 'Entrar' : 'Cadastre-se'} <span aria-hidden="true">↗</span>
              </a>
            </span>
          )}
        </header>
        <main id="main-content" tabIndex={-1}>
          {api.hasSession() && protectedPage && (
            <nav className="account-nav" aria-label="Área acadêmica">
              <a href="#/perfil" aria-current={page === 'perfil' ? 'page' : undefined}>
                Meu cadastro
              </a>
              <a href="#/turmas" aria-current={page === 'turmas' ? 'page' : undefined}>
                Turmas
              </a>
              <a href="#/matriculas" aria-current={page === 'matriculas' ? 'page' : undefined}>
                Matrículas
              </a>
              <a href="#/trabalhos" aria-current={page === 'trabalhos' ? 'page' : undefined}>
                Trabalhos
              </a>
              <a href="#/reunioes" aria-current={page === 'reunioes' ? 'page' : undefined}>
                Reuniões
              </a>
              <a
                href="#/monitoramento"
                aria-current={page === 'monitoramento' ? 'page' : undefined}
              >
                Monitorar Prazos
              </a>
            </nav>
          )}
          {page === 'cadastro' && (
            <AccountForm
              key="signup"
              onRegistered={(address) => {
                setEmail(address);
                navigate('entrar');
              }}
            />
          )}
          {page === 'entrar' && (
            <LoginForm initialEmail={email} notice={notice} onLogin={() => navigate('perfil')} />
          )}
          {page === 'perfil' && api.hasSession() && <Profile onSessionEnded={sessionEnded} />}
          {page === 'turmas' && api.hasSession() && <Classes onSessionEnded={sessionEnded} />}
          {page === 'matriculas' && api.hasSession() && (
            <Enrollments onSessionEnded={sessionEnded} />
          )}
          {page === 'trabalhos' && api.hasSession() && <Works onSessionEnded={sessionEnded} />}
          {page === 'reunioes' && api.hasSession() && <Meetings onSessionEnded={sessionEnded} />}
          {page === 'monitoramento' && api.hasSession() && (
            <Monitoring onSessionEnded={sessionEnded} />
          )}
        </main>
        <footer className="page-footer">
          <span>SIGG-TCC · Equipe Compila-dores</span>
          <span>Conhecimento em conexão.</span>
        </footer>
      </div>
    </div>
  );
}

function AccountForm({
  original,
  etag,
  onRegistered,
  onSaved,
  onReload,
  onSessionEnded,
}: {
  original?: User;
  etag?: string;
  onRegistered?: (email: string) => void;
  onSaved?: (user: User, etag: string | null) => void;
  onReload?: () => void;
  onSessionEnded?: (message: string) => void;
}) {
  const [values, setValues] = useState<FormValues>(() =>
    original ? fromUser(original) : { ...emptyForm },
  );
  const [errors, setErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState('');
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<User | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseStatus, setCourseStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [courseAttempt, setCourseAttempt] = useState(0);
  const student = values.tipo_cadastro === 'aluno';

  useEffect(() => {
    if (!student) return;
    let active = true;
    const controller = new AbortController();
    setCourseStatus('loading');
    api
      .courses(controller.signal)
      .then((result) => {
        if (active) {
          setCourses(result);
          setCourseStatus('ready');
        }
      })
      .catch(() => {
        if (active) setCourseStatus('error');
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [student, original, courseAttempt]);

  function update(name: keyof FormValues, value: string) {
    setValues((previous) => ({ ...previous, [name]: value }));
    setErrors((previous) => ({ ...previous, [name]: undefined }));
  }
  const field = (name: keyof FormValues, hint = false) => ({
    ...inputA11y(name, errors, hint),
    value: values[name],
    onChange: (
      event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
    ) => update(name, event.target.value),
    disabled: busy,
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const issues = validate(values, original);
    if (
      student &&
      !original &&
      (courseStatus !== 'ready' ||
        !courses.some((course) => String(course.id_curso) === values.id_curso))
    )
      issues.id_curso = 'Selecione um curso disponível no sistema.';
    setErrors(issues);
    setConflict(false);
    if (Object.keys(issues).length) {
      setMessage(
        Object.values(issues).includes('Informe um endereço de e-mail válido.')
          ? 'Informe um endereço de e-mail válido.'
          : 'Preencha todos os campos obrigatórios.',
      );
      document.getElementById(Object.keys(issues)[0])?.focus();
      return;
    }
    if (original && !etag) {
      setMessage(
        'Não foi possível verificar a versão do cadastro. Recarregue os dados antes de salvar.',
      );
      setConflict(true);
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      const result = original
        ? await api.update(payload(values, original), etag!)
        : await api.signup(payload(values));
      if (original) {
        if (values.email_usuario.trim().toLowerCase() !== original.email_usuario) {
          onSessionEnded?.('E-mail atualizado com sucesso. Entre novamente com o novo endereço.');
        } else onSaved?.(result.body.data, result.etag);
      } else {
        setReceipt(result.body.data);
        setValues({ ...emptyForm });
      }
    } catch (error) {
      const details = errorDetails(error);
      setErrors(details.fields);
      setMessage(details.message);
      if (error instanceof ApiError && [412, 428].includes(error.status)) setConflict(true);
      if (
        original &&
        error instanceof ApiError &&
        error.status === 401 &&
        error.code !== 'CREDENCIAIS_INVALIDAS'
      )
        onSessionEnded?.('Sua sessão expirou. Entre novamente para acessar seu cadastro.');
    } finally {
      setBusy(false);
    }
  }

  if (receipt)
    return (
      <section className="receipt">
        <span className="success-icon">
          <Icon name="check" size={36} />
        </span>
        <span className="eyebrow">TUDO PRONTO PARA COMEÇAR</span>
        <h2>Boas-vindas ao SIGG-TCC!</h2>
        <Notice success message="Cadastro realizado com sucesso!" />
        <p>
          Sua conta foi criada para <strong>{receipt.email_usuario}</strong>. Agora você já pode
          entrar na plataforma.
        </p>
        <dl className="receipt-details">
          <div>
            <dt>Código do cadastro</dt>
            <dd>#{receipt.id_usuario}</dd>
          </div>
          <div>
            <dt>Tipo de cadastro</dt>
            <dd>{receipt.docente ? 'Docente / avaliador' : 'Estudante'}</dd>
          </div>
        </dl>
        {receipt.docente && (
          <p className="muted">
            As permissões de orientação, avaliação e gestão são atribuídas pela administração
            conforme seu vínculo acadêmico.
          </p>
        )}
        <button className="primary" onClick={() => onRegistered?.(receipt.email_usuario)}>
          Ir para o login <Icon name="arrow" size={18} />
        </button>
      </section>
    );

  return (
    <section className="account-section">
      {!original && (
        <div className="page-intro">
          <span className="eyebrow">
            <span className="tiny-dot" /> FAÇA PARTE DESSA JORNADA
          </span>
          <h2>Crie sua conta</h2>
          <p>Preencha seus dados para começar no SIGG-TCC.</p>
        </div>
      )}
      <form
        onSubmit={submit}
        noValidate
        aria-label={original ? 'Editar meu cadastro' : 'Cadastro de usuário'}
        aria-busy={busy}
      >
        {!original && (
          <fieldset className="account-type" disabled={busy}>
            <legend>Como você participa do TCC?</legend>
            <div className="type-options">
              {(['aluno', 'docente'] as const).map((kind) => (
                <label
                  key={kind}
                  className={`type-option ${values.tipo_cadastro === kind ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="tipo_cadastro"
                    value={kind}
                    checked={values.tipo_cadastro === kind}
                    onChange={() => {
                      update('tipo_cadastro', kind);
                      setErrors({});
                      setMessage('');
                    }}
                  />
                  <span className="type-icon">
                    <Icon name={kind === 'aluno' ? 'cap' : 'book'} size={23} />
                  </span>
                  <span>
                    <strong>
                      {kind === 'aluno' ? 'Sou estudante' : 'Sou docente / avaliador'}
                    </strong>
                    <small>
                      {kind === 'aluno'
                        ? 'Estudante de TCC1 ou TCC2'
                        : 'Orientação, banca ou gestão'}
                    </small>
                  </span>
                  <span className="radio-mark" aria-hidden="true">
                    {values.tipo_cadastro === kind && <span />}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
        )}
        {message && (
          <Notice message={message}>
            {conflict && (
              <button className="text-button" type="button" onClick={onReload}>
                Recarregar cadastro
              </button>
            )}
          </Notice>
        )}
        <div className="section-heading">
          <span>01</span>
          <h3>Dados pessoais{!original && ' e acesso'}</h3>
          <small>Campos obrigatórios, salvo indicação</small>
        </div>
        <div className="fields-grid">
          <div className="full">
            <Field name="nome_usuario" label="Nome completo" errors={errors}>
              <input
                {...field('nome_usuario')}
                autoComplete="name"
                placeholder="Digite seu nome completo"
                maxLength={200}
                required
              />
            </Field>
          </div>
          <div className="full">
            <Field name="email_usuario" label="E-mail" errors={errors}>
              <input
                {...field('email_usuario')}
                type="email"
                autoComplete="email"
                placeholder="seu.nome@exemplo.com"
                maxLength={254}
                required
              />
            </Field>
          </div>
          {!original && (
            <>
              <Field name="senha" label="Senha" errors={errors} hint="Use de 12 a 128 caracteres.">
                <Password
                  {...field('senha', true)}
                  label="Senha"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={128}
                  required
                  placeholder="Crie uma senha segura"
                />
              </Field>
              <Field name="confirmacao_senha" label="Confirmar senha" errors={errors}>
                <Password
                  {...field('confirmacao_senha')}
                  label="Confirmação de senha"
                  autoComplete="new-password"
                  maxLength={128}
                  required
                  placeholder="Digite a senha novamente"
                />
              </Field>
            </>
          )}
          {original && values.email_usuario.trim().toLowerCase() !== original.email_usuario && (
            <div className="full">
              <Field
                name="senha_atual"
                label="Senha atual"
                errors={errors}
                hint="Ao alterar o e-mail, será necessário entrar novamente."
              >
                <Password
                  {...field('senha_atual', true)}
                  label="Senha atual"
                  autoComplete="current-password"
                  required
                />
              </Field>
            </div>
          )}
        </div>
        <div className="section-heading">
          <span>02</span>
          <h3>Informações acadêmicas</h3>
        </div>
        <div className="fields-grid">
          {student ? (
            <>
              <Field name="matricula_aluno" label="Matrícula" errors={errors}>
                <input
                  {...field('matricula_aluno')}
                  disabled={busy || !!original}
                  autoComplete="off"
                  maxLength={30}
                  placeholder="Informe sua matrícula"
                  required
                />
              </Field>
              {original ? (
                <div className="field">
                  <label htmlFor="curso-cadastrado">Curso</label>
                  <input
                    id="curso-cadastrado"
                    value={
                      courses.find((course) => String(course.id_curso) === values.id_curso)
                        ?.nome_curso ||
                      (courseStatus === 'loading'
                        ? 'Carregando curso…'
                        : 'Curso vinculado ao seu cadastro')
                    }
                    disabled
                  />
                  <small>Matrícula e curso são mantidos pela instituição.</small>
                </div>
              ) : (
                <Field name="id_curso" label="Curso" errors={errors}>
                  <select
                    {...field('id_curso')}
                    disabled={busy || courseStatus !== 'ready' || !courses.length}
                    required
                  >
                    <option value="">
                      {courseStatus === 'loading' ? 'Carregando cursos…' : 'Selecione seu curso'}
                    </option>
                    {courses.map((course) => (
                      <option key={course.id_curso} value={course.id_curso}>
                        {course.nome_curso}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
              {!original && courseStatus === 'error' && (
                <div className="inline-warning full" role="alert">
                  Não foi possível carregar os cursos.{' '}
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => setCourseAttempt((value) => value + 1)}
                  >
                    Tentar novamente
                  </button>
                </div>
              )}
              {!original && courseStatus === 'ready' && !courses.length && (
                <div className="inline-warning full" role="status">
                  Nenhum curso ativo disponível. Solicite à administração o cadastro do seu curso.
                </div>
              )}
            </>
          ) : (
            <>
              <Field name="titulacao_docente" label="Titulação" errors={errors}>
                <select {...field('titulacao_docente')} required>
                  <option value="">Selecione sua titulação</option>
                  <option value="especialista">Especialista</option>
                  <option value="mestre">Mestre</option>
                  <option value="doutor">Doutor</option>
                </select>
              </Field>
              <Field name="tipo_docente" label="Vínculo institucional" errors={errors}>
                <select {...field('tipo_docente')} disabled={busy || !!original}>
                  <option value="interno">Docente interno · UEA</option>
                  <option value="externo">Docente / avaliador externo</option>
                </select>
              </Field>
              <div className="full">
                <Field
                  name="instituicao_origem_docente"
                  label="Instituição de origem"
                  optional
                  errors={errors}
                >
                  <input
                    {...field('instituicao_origem_docente')}
                    autoComplete="organization"
                    maxLength={200}
                    placeholder="Nome da instituição"
                  />
                </Field>
              </div>
              <div className="full">
                <Field
                  name="areas_interesse"
                  label="Áreas de interesse"
                  optional
                  errors={errors}
                  hint="Separe por vírgulas. Até 20 áreas."
                >
                  <input
                    {...field('areas_interesse', true)}
                    placeholder="Ex.: Engenharia de Software, Inteligência Artificial"
                  />
                </Field>
              </div>
              <div className="full">
                <Field
                  name="url_lattes_docente"
                  label="Link do Currículo Lattes"
                  optional
                  errors={errors}
                >
                  <input
                    {...field('url_lattes_docente')}
                    type="url"
                    maxLength={2048}
                    placeholder="https://lattes.cnpq.br/…"
                  />
                </Field>
              </div>
            </>
          )}
        </div>
        {!original && !student && (
          <p className="permission-note">
            <Icon name="shield" size={18} />
            <span>
              Seu cadastro não concede permissões de gestão. Os acessos são definidos pela
              administração, conforme seu vínculo.
            </span>
          </p>
        )}
        <div className="submit-row">
          <button
            className="primary"
            disabled={
              busy ||
              conflict ||
              (!original && student && (courseStatus !== 'ready' || !courses.length))
            }
            type="submit"
          >
            {busy ? 'Salvando…' : original ? 'Salvar alterações' : 'Criar minha conta'}
            {!busy && <Icon name="arrow" size={18} />}
          </button>
          {original && (
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => {
                setValues(fromUser(original));
                setErrors({});
                setMessage('');
                setConflict(false);
              }}
            >
              Descartar alterações
            </button>
          )}
        </div>
        {!original && (
          <p className="form-footnote">
            <Icon name="shield" size={15} />
            <span>
              Seus dados serão utilizados para sua participação no processo acadêmico de TCC.
            </span>
          </p>
        )}
      </form>
      {!original && (
        <div className="login-prompt">
          Já faz parte do SIGG-TCC? <a href="#/entrar">Entre na sua conta</a>
        </div>
      )}
    </section>
  );
}

function LoginForm({
  initialEmail,
  notice,
  onLogin,
}: {
  initialEmail: string;
  notice: string;
  onLogin: () => void;
}) {
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const issues: FieldErrors = {};
    if (!validEmail(email)) issues.email_usuario = 'Informe um endereço de e-mail válido.';
    if (!password) issues.senha = 'Informe sua senha.';
    setErrors(issues);
    if (Object.keys(issues).length) {
      setMessage('Revise seu e-mail e sua senha.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      await api.login(email.trim().toLowerCase(), password);
      setPassword('');
      onLogin();
    } catch (error) {
      setMessage(errorDetails(error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="login-section">
      <div className="page-intro">
        <span className="eyebrow">BOM TER VOCÊ DE VOLTA</span>
        <h2>Entre na sua conta</h2>
        <p>Acesse e mantenha seu cadastro atualizado.</p>
      </div>
      {notice && <Notice success message={notice} />}
      {message && <Notice message={message} />}
      <form onSubmit={submit} noValidate aria-label="Entrar na conta" aria-busy={busy}>
        <Field name="email_usuario" label="E-mail" errors={errors}>
          <input
            {...inputA11y('email_usuario', errors)}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={busy}
          />
        </Field>
        <Field name="senha" label="Senha" errors={errors}>
          <Password
            {...inputA11y('senha', errors)}
            label="Senha"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
          />
        </Field>
        <button className="primary" disabled={busy}>
          {busy ? 'Entrando…' : 'Entrar'} <Icon name="arrow" size={18} />
        </button>
      </form>
      <div className="login-prompt">
        É sua primeira vez aqui? <a href="#/cadastro">Crie sua conta</a>
      </div>
    </section>
  );
}

function Profile({ onSessionEnded }: { onSessionEnded: (message: string) => void }) {
  const [user, setUser] = useState<User | null>(null);
  const [etag, setEtag] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState('');
  const [version, setVersion] = useState(0);
  const [removing, setRemoving] = useState(false);
  const sessionEnded = useRef(onSessionEnded);
  sessionEnded.current = onSessionEnded;
  const load = useCallback(async () => {
    setMessage('');
    setSuccess('');
    try {
      const result = await api.profile();
      setUser(result.body.data);
      setEtag(result.etag);
      setVersion((value) => value + 1);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401)
        sessionEnded.current('Sua sessão expirou. Entre novamente.');
      else setMessage(errorDetails(error).message);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <section className="profile-section">
      <div className="page-intro">
        <span className="eyebrow">SUA CONTA NO SIGG-TCC</span>
        <h2>Meu cadastro</h2>
        <p>Consulte e atualize suas informações.</p>
      </div>
      {message && (
        <Notice message={message}>
          <button type="button" className="text-button" onClick={load}>
            Tentar novamente
          </button>
        </Notice>
      )}
      {success && <Notice success message={success} />}
      {!user && !message && <p role="status">Carregando seu cadastro…</p>}
      {user && (
        <>
          <div className="profile-summary">
            <span className="avatar">{user.nome_usuario.trim().slice(0, 1).toUpperCase()}</span>
            <div>
              <strong>{user.nome_usuario}</strong>
              <small>
                Cadastro #{user.id_usuario} · {user.docente ? 'Docente / avaliador' : 'Estudante'}
              </small>
            </div>
            <span className="active-badge">Conta ativa</span>
          </div>
          <AccountForm
            key={version}
            original={user}
            etag={etag || undefined}
            onSaved={(updated, nextEtag) => {
              setUser(updated);
              setEtag(nextEtag);
              setVersion((value) => value + 1);
              setSuccess('Cadastro atualizado com sucesso!');
            }}
            onReload={load}
            onSessionEnded={onSessionEnded}
          />
          <p className="updated-at">
            Última atualização:{' '}
            {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(
              new Date(user.data_atualizacao_usuario),
            )}
          </p>
          <div className="danger-zone">
            <div>
              <h3>Inativar minha conta</h3>
              <p>Seu acesso será encerrado. O histórico acadêmico será preservado.</p>
            </div>
            <button
              type="button"
              className="danger-outline"
              onClick={() => setRemoving(true)}
              disabled={!etag}
            >
              Inativar conta
            </button>
          </div>
          {removing && etag && (
            <DeactivateDialog
              etag={etag}
              onCancel={() => setRemoving(false)}
              onComplete={() => onSessionEnded('Sua conta foi inativada com sucesso.')}
              onExpired={onSessionEnded}
              onConflict={() => {
                setRemoving(false);
                setMessage(
                  'O cadastro foi alterado. Recarregue os dados antes de inativar a conta.',
                );
              }}
            />
          )}
        </>
      )}
    </section>
  );
}

function DeactivateDialog({
  etag,
  onCancel,
  onComplete,
  onExpired,
  onConflict,
}: {
  etag: string;
  onCancel: () => void;
  onComplete: () => void;
  onExpired: (message: string) => void;
  onConflict: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [secret, setSecret] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const modal = dialog.current!;
    modal.showModal();
    return () => modal.close();
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!secret) {
      setMessage('Informe sua senha atual para confirmar.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      await api.deactivate(secret, etag);
      setSecret('');
      onComplete();
    } catch (error) {
      if (error instanceof ApiError && [412, 428].includes(error.status)) onConflict();
      else if (
        error instanceof ApiError &&
        error.status === 401 &&
        error.code !== 'CREDENCIAIS_INVALIDAS'
      )
        onExpired('Sua sessão expirou. Entre novamente.');
      else setMessage(errorDetails(error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="confirm-dialog"
      aria-labelledby="deactivate-title"
      aria-describedby="deactivate-description"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <h2 id="deactivate-title">Inativar sua conta?</h2>
      <p id="deactivate-description">
        Você perderá o acesso à plataforma e suas sessões serão encerradas. Seus registros
        acadêmicos serão mantidos.
      </p>
      {message && <Notice message={message} />}
      <form onSubmit={submit} noValidate>
        <label htmlFor="deactivate-password">Confirme sua senha atual</label>
        <Password
          id="deactivate-password"
          label="Senha de confirmação"
          value={secret}
          onChange={(event) => setSecret(event.target.value)}
          autoComplete="current-password"
          disabled={busy}
          required
        />
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onCancel} disabled={busy}>
            Manter minha conta
          </button>
          <button className="danger" disabled={busy}>
            {busy ? 'Inativando…' : 'Confirmar inativação'}
          </button>
        </div>
      </form>
    </dialog>
  );
}
