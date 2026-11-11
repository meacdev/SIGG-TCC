import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Field, Icon, Notice, Password, inputA11y } from './components';
import { validEmail } from './validation';

type Step = 'email' | 'codigo' | 'senha';
type Errors = Record<string, string | undefined>;

export function RecoveryForm({
  initialEmail,
  onCompleted,
}: {
  initialEmail: string;
  onCompleted: (email: string) => void;
}) {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState('');
  const [recoveryId, setRecoveryId] = useState('');
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    heading.current?.focus();
  }, [step]);
  useEffect(() => {
    if (!cooldown) return;
    const timer = window.setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  function restart() {
    setStep('email');
    setCode('');
    setRecoveryId('');
    setToken('');
    setPassword('');
    setConfirmation('');
    setErrors({});
    setMessage('');
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const issues: Errors = {};
    if (step === 'email' && !validEmail(email))
      issues.email_usuario = 'Informe um endereço de e-mail válido.';
    if (step === 'codigo' && !/^[0-9]{10}$/.test(code))
      issues.codigo = 'Informe os 10 dígitos do código recebido por e-mail.';
    if (step === 'senha') {
      if (password.length < 12 || password.length > 128 || !password.trim())
        issues.nova_senha = 'Use de 12 a 128 caracteres.';
      if (password !== confirmation)
        issues.confirmacao_senha = 'A confirmação da senha não confere.';
    }
    setErrors(issues);
    if (Object.keys(issues).length) {
      setMessage('Revise os campos indicados para continuar.');
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      if (step === 'email') {
        const result = await api.requestReset(email.trim().toLowerCase());
        if (!active.current) return;
        setEmail(email.trim().toLowerCase());
        setRecoveryId(result.body.data.id_recuperacao);
        setCooldown(60);
        setStep('codigo');
      } else if (step === 'codigo') {
        const result = await api.verifyReset(recoveryId, code);
        if (!active.current) return;
        setToken(result.body.data.token_redefinicao);
        setCode('');
        setStep('senha');
      } else {
        await api.resetPassword({
          id_recuperacao: recoveryId,
          token_redefinicao: token,
          nova_senha: password,
          confirmacao_senha: confirmation,
        });
        if (!active.current) return;
        setToken('');
        setPassword('');
        setConfirmation('');
        onCompleted(email);
      }
    } catch (error) {
      if (!active.current) return;
      setMessage(
        error instanceof ApiError
          ? error.message
          : 'Não foi possível concluir a recuperação. Tente novamente.',
      );
      if (error instanceof ApiError) {
        const fields: Errors = { ...error.fields };
        if (error.code === 'SENHA_INVALIDA') fields.nova_senha = error.message;
        if (error.code === 'SENHAS_DIFERENTES') fields.confirmacao_senha = error.message;
        if (error.code === 'CODIGO_INVALIDO') fields.codigo = error.message;
        setErrors(fields);
      }
    } finally {
      if (active.current) setBusy(false);
    }
  }

  const index = step === 'email' ? 0 : step === 'codigo' ? 1 : 2;
  return (
    <section className="login-section recovery-section">
      <div className="page-intro">
        <span className="eyebrow">VAMOS RECUPERAR SEU ACESSO</span>
        <h1 ref={heading} tabIndex={-1}>
          {step === 'email'
            ? 'Esqueceu sua senha?'
            : step === 'codigo'
              ? 'Confira seu e-mail'
              : 'Crie uma nova senha'}
        </h1>
        <p>
          {step === 'email'
            ? 'Informe o e-mail cadastrado para receber um código de recuperação.'
            : step === 'codigo'
              ? `Se houver uma conta ativa para ${email}, enviaremos o código. Confira também o spam.`
              : 'Escolha uma senha segura para voltar ao SIGG-TCC.'}
        </p>
      </div>
      <ol className="recovery-progress" aria-label="Etapas da recuperação">
        {['E-mail', 'Código', 'Nova senha'].map((label, i) => (
          <li key={label} aria-current={index === i ? 'step' : undefined}>
            <span>{i + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      {message && <Notice message={message} />}
      <form onSubmit={submit} noValidate aria-label="Recuperar senha" aria-busy={busy}>
        {step === 'email' && (
          <Field name="email_usuario" label="E-mail" errors={errors}>
            <input
              {...inputA11y('email_usuario', errors)}
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={busy}
              required
            />
          </Field>
        )}
        {step === 'codigo' && (
          <Field
            name="codigo"
            label="Código de recuperação"
            errors={errors}
            hint="Digite os 10 dígitos recebidos. São permitidas até 5 tentativas; cada novo envio invalida o código anterior."
          >
            <input
              {...inputA11y('codigo', errors, true)}
              className="recovery-code"
              type="text"
              autoComplete="one-time-code"
              inputMode="numeric"
              spellCheck={false}
              maxLength={10}
              pattern="[0-9]{10}"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              disabled={busy}
              required
            />
          </Field>
        )}
        {step === 'senha' && (
          <>
            <Field
              name="nova_senha"
              label="Nova senha"
              errors={errors}
              hint="Use de 12 a 128 caracteres."
            >
              <Password
                {...inputA11y('nova_senha', errors, true)}
                label="Nova senha"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={busy}
                required
              />
            </Field>
            <Field name="confirmacao_senha" label="Confirmação de senha" errors={errors}>
              <Password
                {...inputA11y('confirmacao_senha', errors)}
                label="Confirmação de senha"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                disabled={busy}
                required
              />
            </Field>
          </>
        )}
        <button className="primary" disabled={busy || (step === 'email' && cooldown > 0)}>
          {busy
            ? 'Aguarde…'
            : step === 'email'
              ? cooldown
                ? `Aguarde ${cooldown}s para reenviar`
                : 'Enviar código'
              : step === 'codigo'
                ? 'Continuar'
                : 'Confirmar'}
          <Icon name="arrow" size={18} />
        </button>
        {step !== 'email' && (
          <button
            className="text-button recovery-restart"
            type="button"
            disabled={busy}
            onClick={restart}
          >
            Solicitar novo código ou alterar e-mail
          </button>
        )}
      </form>
      <div className="login-prompt">
        <a href="#/entrar">Voltar para o login</a>
      </div>
    </section>
  );
}
