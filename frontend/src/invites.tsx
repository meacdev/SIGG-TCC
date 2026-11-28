import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { failure } from './academic';
import { Field, Icon, Notice, Password, inputA11y } from './components';
import { formatDate } from './admin-users';
import { forgetLinkToken, linkToken } from './link-token';
import { PASSWORD_RULE, validPassword } from './validation';

interface Invitation {
  nome_usuario: string;
  email_usuario: string;
  data_expiracao_convite: string;
}
type Errors = Record<string, string | undefined>;

const LINK_HINT = 'Abra o link completo recebido por e-mail ou solicite um novo à secretaria.';

/** UC14: quem foi pré-cadastrado define a própria senha pelo link do convite. */
export function AcceptInvite({ onAccepted }: { onAccepted: (email: string) => void }) {
  const [token] = useState(() => linkToken('aceitar-convite'));
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [message, setMessage] = useState(token ? '' : LINK_HINT);
  const [loading, setLoading] = useState(!!token);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    let active = true;
    api
      .request<Invitation>('/auth/convite/validar', {
        method: 'POST',
        body: JSON.stringify({ token }),
      })
      .then((result) => {
        if (active) setInvitation(result.body.data);
      })
      .catch((error) => {
        if (active) setMessage(failure(error));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !invitation) return;
    const issues: Errors = {};
    if (!validPassword(password)) issues.nova_senha = PASSWORD_RULE;
    if (!confirmation) issues.confirmacao_senha = 'Confirme sua senha.';
    else if (confirmation !== password) issues.confirmacao_senha = 'As senhas não coincidem.';
    setErrors(issues);
    if (Object.keys(issues).length) {
      setMessage('Revise os campos indicados para continuar.');
      document.getElementById(Object.keys(issues)[0])?.focus();
      return;
    }
    setBusy(true);
    setMessage('');
    try {
      await api.request<void>('/auth/convite/aceitar', {
        method: 'POST',
        body: JSON.stringify({ token, nova_senha: password, confirmacao_senha: confirmation }),
      });
      forgetLinkToken('aceitar-convite');
      setPassword('');
      setConfirmation('');
      onAccepted(invitation.email_usuario);
    } catch (error) {
      setMessage(failure(error));
      if (error instanceof ApiError) setErrors(error.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="login-section">
      <div className="page-intro">
        <span className="eyebrow">CONVITE DA SECRETARIA</span>
        <h1>Ative sua conta</h1>
        <p>Defina a senha que você usará para entrar no SIGG-TCC.</p>
      </div>
      {loading && <p role="status">Verificando o convite…</p>}
      {message && <Notice message={message} />}
      {invitation && (
        <form onSubmit={submit} noValidate aria-label="Ativar conta" aria-busy={busy}>
          <dl className="receipt-details invite-details">
            <div>
              <dt>Nome</dt>
              <dd>{invitation.nome_usuario}</dd>
            </div>
            <div>
              <dt>E-mail de acesso</dt>
              <dd>{invitation.email_usuario}</dd>
            </div>
          </dl>
          <p className="muted">
            Convite válido até {formatDate(invitation.data_expiracao_convite, true)}.
          </p>
          <Field name="nova_senha" label="Nova senha" errors={errors} hint={PASSWORD_RULE}>
            <Password
              {...inputA11y('nova_senha', errors, true)}
              label="Nova senha"
              autoComplete="new-password"
              minLength={8}
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
              maxLength={128}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              disabled={busy}
              required
            />
          </Field>
          <button className="primary" disabled={busy}>
            {busy ? 'Ativando…' : 'Ativar minha conta'} <Icon name="arrow" size={18} />
          </button>
        </form>
      )}
      <div className="login-prompt">
        Já ativou sua conta? <a href="#/entrar">Entre no SIGG-TCC</a>
      </div>
    </section>
  );
}

/**
 * UC14: confirma o novo e-mail definido pelo Administrador. A confirmação exige um clique, para que
 * leitores automáticos de links não consumam o token.
 */
export function ConfirmEmail({ onConfirmed }: { onConfirmed: (message: string) => void }) {
  const [token] = useState(() => linkToken('confirmar-email'));
  const [message, setMessage] = useState(token ? '' : LINK_HINT);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    if (busy) return;
    setBusy(true);
    setMessage('');
    try {
      const result = await api.request<void>('/auth/alteracao-email/confirmar', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });
      forgetLinkToken('confirmar-email');
      onConfirmed(
        `${result.body.message || 'E-mail confirmado com sucesso!'} Entre com o novo endereço.`,
      );
    } catch (error) {
      setMessage(failure(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="login-section">
      <div className="page-intro">
        <span className="eyebrow">ALTERAÇÃO DE E-MAIL</span>
        <h1>Confirme seu novo e-mail</h1>
        <p>
          A secretaria atualizou o e-mail da sua conta. Confirme para passar a entrar com este
          endereço.
        </p>
      </div>
      {message && <Notice message={message} />}
      {token && (
        <button className="primary" type="button" onClick={confirm} disabled={busy}>
          {busy ? 'Confirmando…' : 'Confirmar novo e-mail'} <Icon name="check" size={18} />
        </button>
      )}
      <p className="muted invite-note">
        Se a conta ainda aguarda ativação, um novo convite será enviado para o endereço confirmado.
      </p>
      <div className="login-prompt">
        <a href="#/entrar">Voltar para o login</a>
      </div>
    </section>
  );
}
