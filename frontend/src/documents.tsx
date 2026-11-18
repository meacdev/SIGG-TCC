import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from './api';
import { Notice } from './components';
import { failure, gradeText, type Defense } from './defenses';

interface DocumentState {
  ata: {
    id_documento: number;
    versao: number;
    codigo_verificacao: string;
    data_emissao: string;
    assinada: boolean;
    liberada_aluno: boolean;
  } | null;
  resultado: string | null;
  prazo: string | null;
  correcoes: string | null;
  declaracoes: { id_documento: number; codigo_verificacao: string }[];
  emails: { id_notificacao: number; situacao: string; tentativas: number }[];
}

export async function download(path: string, name: string) {
  const result = await api.download(path);
  const url = URL.createObjectURL(result.body.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function DocumentsPanel({
  defense,
  onVersion,
  onError,
}: {
  defense: Defense;
  onVersion: (version: string) => void;
  onError: (error: unknown) => void;
}) {
  const [state, setState] = useState<DocumentState | null>(null);
  const [version, setVersion] = useState('');
  const [result, setResult] = useState('');
  const [deadline, setDeadline] = useState('');
  const [corrections, setCorrections] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState('');
  const [deliveryMessage, setDeliveryMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  function accept(data: DocumentState, etag: string | null) {
    setState(data);
    setVersion(etag || '');
    onVersion(etag || '');
  }
  useEffect(() => {
    let active = true;
    api
      .request<DocumentState>(`/bancas/${defense.id_banca}/documentos`, {}, true)
      .then((response) => {
        if (!active) return;
        accept(response.body.data, response.etag);
        setResult(response.body.data.resultado || '');
        setDeadline(response.body.data.prazo || '');
        setCorrections(response.body.data.correcoes || '');
      })
      .catch((error) => {
        if (active) {
          setMessage(failure(error));
          if (error instanceof ApiError && error.status === 401) onError(error);
        }
      });
    return () => {
      active = false;
    };
  }, [defense.id_banca, defense.avaliacoes_enviadas, attempt]);
  async function action(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setMessage('');
    setSuccess('');
    setDeliveryMessage('');
    try {
      await work();
    } catch (error) {
      setMessage(failure(error));
      if (error instanceof ApiError && error.status === 401) onError(error);
    } finally {
      setBusy(false);
    }
  }
  async function generate(event: FormEvent) {
    event.preventDefault();
    if (!result) {
      setMessage('Selecione o resultado final da defesa.');
      return;
    }
    if (result === 'aprovado_com_correcoes' && (!deadline || !corrections.trim())) {
      setMessage('Informe o prazo e as correções solicitadas.');
      return;
    }
    if (state?.ata && !reason.trim()) {
      setMessage('Informe a justificativa da reemissão.');
      return;
    }
    await action(async () => {
      const response = await api.request<DocumentState>(
        `/bancas/${defense.id_banca}/ata`,
        {
          method: 'POST',
          headers: { 'If-Match': version },
          body: JSON.stringify({
            resultado: result,
            prazo: deadline || null,
            correcoes: corrections,
            justificativa: reason,
          }),
        },
        true,
      );
      accept(response.body.data, response.etag);
      if (response.body.code === 'UC_10_M07') {
        setDeliveryMessage(response.body.message || 'Há declarações pendentes de envio.');
      } else {
        setSuccess(response.body.message || 'Ata de Defesa gerada com sucesso!');
      }
      setReason('');
    });
  }
  async function signed(event: FormEvent) {
    event.preventDefault();
    if (!file || !confirmed) {
      setMessage('Selecione o PDF e confirme a conferência das assinaturas.');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setMessage('Envie um PDF de até 50 MB.');
      return;
    }
    await action(async () => {
      const form = new FormData();
      form.set('arquivo', file);
      form.set('assinaturas_conferidas', 'true');
      const response = await api.request<DocumentState>(
        `/bancas/${defense.id_banca}/ata/assinada`,
        { method: 'POST', headers: { 'If-Match': version }, body: form },
        true,
      );
      accept(response.body.data, response.etag);
      setSuccess('Arquivo da ata assinada registrado.');
      setFile(null);
      setConfirmed(false);
    });
  }
  return (
    <section className="documents-panel" aria-label="Documentos da defesa">
      <div className="section-heading">
        <span>03</span>
        <h3>Ata e declarações</h3>
      </div>
      {message && (
        <Notice message={message}>
          <button
            className="text-button"
            type="button"
            onClick={() => {
              setAttempt(attempt + 1);
              setMessage('');
            }}
          >
            Atualizar documentos
          </button>
        </Notice>
      )}
      {success && <Notice success message={success} />}
      {deliveryMessage && <Notice message={deliveryMessage} />}
      {!state && !message && <p aria-live="polite">Carregando documentos…</p>}
      {defense.media_final === null && (
        <p className="academic-hint">
          Não é possível gerar a ata enquanto houver avaliações pendentes.
        </p>
      )}
      {state && (
        <>
          {!state.ata?.assinada && (
            <form onSubmit={generate} aria-label="Gerar ata de defesa" noValidate aria-busy={busy}>
              <div className="fields-grid">
                <div className="field">
                  <label htmlFor="resultado-defesa">Resultado da defesa</label>
                  <select
                    id="resultado-defesa"
                    value={result}
                    onChange={(event) => setResult(event.target.value)}
                    disabled={busy}
                    required
                  >
                    <option value="">Selecione o resultado</option>
                    <option value="aprovado">Aprovado</option>
                    <option value="reprovado">Reprovado</option>
                    <option value="aprovado_com_correcoes">Aprovado com Correções</option>
                  </select>
                </div>
                {result === 'aprovado_com_correcoes' && (
                  <>
                    <div className="field">
                      <label htmlFor="prazo-correcao">Prazo para correções</label>
                      <input
                        id="prazo-correcao"
                        type="date"
                        value={deadline}
                        onChange={(event) => setDeadline(event.target.value)}
                        disabled={busy}
                        required
                      />
                    </div>
                    <div className="field full">
                      <label htmlFor="correcoes-solicitadas">Correções solicitadas</label>
                      <textarea
                        id="correcoes-solicitadas"
                        value={corrections}
                        onChange={(event) => setCorrections(event.target.value)}
                        disabled={busy}
                        maxLength={10000}
                        required
                      />
                    </div>
                  </>
                )}
                {state.ata && (
                  <div className="field full">
                    <label htmlFor="justificativa-ata">Justificativa da reemissão</label>
                    <textarea
                      id="justificativa-ata"
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      disabled={busy}
                      maxLength={2000}
                      required
                    />
                  </div>
                )}
              </div>
              <p className="academic-hint">
                {defense.media_final === null
                  ? 'Média ainda não consolidada.'
                  : `Média consolidada: ${gradeText(defense.media_final)} / 10.`}{' '}
                O resultado é registrado pela banca conforme as regras acadêmicas.
              </p>
              <button
                className="primary"
                disabled={busy || !version || defense.media_final === null}
              >
                {busy
                  ? 'Processando…'
                  : state.ata
                    ? 'Gerar nova versão da ata'
                    : 'Gerar ata de defesa'}
              </button>
            </form>
          )}
          {state.ata && (
            <div className="document-box">
              <h3>Ata de Defesa · versão {state.ata.versao}</h3>
              <p className="academic-hint">
                Código de verificação: <code>{state.ata.codigo_verificacao}</code>
              </p>
              <div className="document-actions">
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    action(() => download(`/bancas/${defense.id_banca}/ata`, 'ata-defesa.pdf'))
                  }
                >
                  Baixar ata gerada
                </button>
                {state.ata.assinada && (
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      action(() =>
                        download(
                          `/bancas/${defense.id_banca}/ata?assinada=true`,
                          'ata-assinada.pdf',
                        ),
                      )
                    }
                  >
                    Baixar ata assinada
                  </button>
                )}
              </div>
              <p className="academic-hint">
                {state.ata.liberada_aluno
                  ? 'Ata assinada liberada ao estudante.'
                  : 'A liberação ao estudante exige o arquivo assinado e, quando solicitadas, correções aprovadas pelo orientador.'}
              </p>
            </div>
          )}
          {state.ata && !state.ata.assinada && (
            <form className="document-box" onSubmit={signed} aria-label="Registrar ata assinada">
              <h3>Registrar arquivo assinado</h3>
              <p className="academic-hint">
                Após colher e conferir as assinaturas, envie o arquivo correspondente a esta versão
                da ata. PDF de até 50 MB.
              </p>
              <div className="field">
                <label htmlFor="ata-assinada">Arquivo da ata assinada</label>
                <input
                  id="ata-assinada"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                  disabled={busy}
                />
              </div>
              <label className="confirmation-check">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                  disabled={busy}
                />
                Conferi as assinaturas dos membros e o conteúdo desta ata.
              </label>
              <button className="primary" disabled={busy}>
                Registrar ata assinada
              </button>
            </form>
          )}
          {state.declaracoes.length > 0 && (
            <div className="document-box">
              <h3>Declarações de participação</h3>
              <div className="document-actions">
                {state.declaracoes.map((document, index) => (
                  <button
                    className="secondary"
                    key={document.id_documento}
                    disabled={busy}
                    onClick={() =>
                      action(() =>
                        download(
                          `/bancas/${defense.id_banca}/declaracoes/${document.id_documento}`,
                          `declaracao-${index + 1}.pdf`,
                        ),
                      )
                    }
                  >
                    Baixar declaração {index + 1}
                  </button>
                ))}
              </div>
              <p className="academic-hint">
                {state.emails.filter((n) => n.situacao === 'enviada').length} de{' '}
                {state.emails.length} e-mails enviados.
              </p>
              {state.emails.some((n) => n.situacao !== 'enviada') && (
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      const response = await api.request<DocumentState>(
                        `/bancas/${defense.id_banca}/declaracoes/reenvio`,
                        { method: 'POST' },
                        true,
                      );
                      accept(response.body.data, response.etag);
                      if (response.body.code === 'UC_10_M07') {
                        setDeliveryMessage(
                          response.body.message || 'Há declarações pendentes de envio.',
                        );
                      } else {
                        setSuccess(response.body.message || 'Declarações enviadas.');
                      }
                    })
                  }
                >
                  Tentar enviar declarações novamente
                </button>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

export function StudentDocuments({
  onSessionEnded,
}: {
  onSessionEnded: (message: string) => void;
}) {
  const [items, setItems] = useState<
    { id_banca: number; titulo: string; resultado: string; assinada: boolean; liberada: boolean }[]
  >([]);
  const [message, setMessage] = useState('');
  useEffect(() => {
    api
      .request<typeof items>('/minhas-atas', {}, true)
      .then((result) => setItems(result.body.data))
      .catch((error) => setMessage(failure(error)));
  }, []);
  return (
    <section className="defense-portal">
      <div className="page-intro">
        <span className="eyebrow">DOCUMENTOS ACADÊMICOS</span>
        <h2>Minhas atas</h2>
        <p>Acompanhe a liberação dos documentos do seu trabalho.</p>
      </div>
      {message && <Notice message={message} />}
      {!items.length && !message && (
        <p className="academic-hint">Nenhuma ata disponível para seu cadastro.</p>
      )}
      {items.map((item) => (
        <article className="document-box" key={item.id_banca}>
          <h3>{item.titulo}</h3>
          <p className="academic-hint">
            {item.liberada
              ? 'Ata assinada liberada.'
              : 'Aguardando registro da ata assinada e conclusão das correções, quando exigidas.'}
          </p>
          <button
            className="primary"
            disabled={!item.liberada}
            onClick={() =>
              download(`/bancas/${item.id_banca}/ata?assinada=true`, 'ata-assinada.pdf').catch(
                (error) => {
                  setMessage(failure(error));
                  if (!api.hasSession()) onSessionEnded('Entre novamente para baixar sua ata.');
                },
              )
            }
          >
            Baixar minha ata assinada
          </button>
        </article>
      ))}
    </section>
  );
}

export function VerifyDocument() {
  const [code, setCode] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [result, setResult] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    setResult('');
    try {
      const response = await api.request<{
        vigente: boolean;
        tipo: string;
        sha256: string;
        sha256_assinado: string | null;
      }>(`/documentos/verificar?codigo=${encodeURIComponent(code.trim())}`);
      if (!response.body.data.vigente) {
        setMessage('Este documento foi revogado ou substituído.');
        return;
      }
      if (file) {
        if (file.size > 50 * 1024 * 1024) throw new Error('Selecione um arquivo de até 50 MB.');
        const hash = Array.from(
          new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())),
        )
          .map((byte) => byte.toString(16).padStart(2, '0'))
          .join('');
        if (![response.body.data.sha256, response.body.data.sha256_assinado].includes(hash)) {
          setMessage('O arquivo selecionado não corresponde ao documento registrado.');
          return;
        }
        setResult('Documento vigente. O arquivo corresponde ao registro do SIGG-TCC.');
      } else
        setResult(
          'Código de documento vigente encontrado. Selecione o PDF para comparar também a integridade do arquivo.',
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
        <span className="eyebrow">CONSULTA PÚBLICA</span>
        <h2>Verificar documento</h2>
        <p>Confira o código impresso na ata ou declaração.</p>
      </div>
      {message && <Notice message={message} />}
      {result && <Notice success message={result} />}
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="codigo-documento">Código de verificação</label>
          <input
            id="codigo-documento"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            maxLength={100}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="pdf-verificacao">PDF para comparação (opcional)</label>
          <input
            id="pdf-verificacao"
            type="file"
            accept="application/pdf,.pdf"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </div>
        <button className="primary" disabled={busy}>
          {busy ? 'Verificando…' : 'Verificar documento'}
        </button>
      </form>
      <p className="academic-hint">
        A consulta confere o registro e a integridade do arquivo. Ela não substitui a verificação
        das assinaturas e dos certificados dos signatários.
      </p>
    </section>
  );
}
