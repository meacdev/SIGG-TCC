import type { FieldErrors, FormValues, User } from './types';

export const emptyForm: FormValues = {
  nome_usuario: '',
  email_usuario: '',
  senha: '',
  confirmacao_senha: '',
  tipo_cadastro: 'aluno',
  titulacao_docente: '',
  tipo_docente: 'interno',
  instituicao_origem_docente: '',
  areas_interesse: '',
  url_lattes_docente: '',
  matricula_aluno: '',
  id_curso: '',
  senha_atual: '',
};

export const parseAreas = (value: string) => [
  ...new Set(
    value
      .split(',')
      .map((area) => area.trim())
      .filter(Boolean),
  ),
];
export const validEmail = (email: string) => /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/.test(email.trim());

export function fromUser(user: User): FormValues {
  return {
    ...emptyForm,
    nome_usuario: user.nome_usuario,
    email_usuario: user.email_usuario,
    tipo_cadastro: user.docente ? 'docente' : 'aluno',
    titulacao_docente: user.docente?.titulacao_docente || '',
    tipo_docente: user.docente?.tipo_docente || 'interno',
    areas_interesse: user.docente?.areas_interesse.join(', ') || '',
    url_lattes_docente: user.docente?.url_lattes_docente || '',
    instituicao_origem_docente: user.docente?.instituicao_origem_docente || '',
    matricula_aluno: user.aluno?.matricula_aluno || '',
    id_curso: String(user.aluno?.id_curso || ''),
  };
}

export function validate(values: FormValues, original?: User): FieldErrors {
  const errors: FieldErrors = {};
  if (!values.nome_usuario.trim()) errors.nome_usuario = 'Informe seu nome completo.';
  else if (values.nome_usuario.trim().length > 200) errors.nome_usuario = 'Use até 200 caracteres.';
  if (!values.email_usuario.trim()) errors.email_usuario = 'Informe seu e-mail.';
  else if (!validEmail(values.email_usuario) || values.email_usuario.trim().length > 254)
    errors.email_usuario = 'Informe um endereço de e-mail válido.';
  if (!original) {
    if (values.senha.length < 12 || values.senha.length > 128 || !values.senha.trim())
      errors.senha = 'A senha deve conter de 12 a 128 caracteres.';
    if (!values.confirmacao_senha) errors.confirmacao_senha = 'Confirme sua senha.';
    else if (values.confirmacao_senha !== values.senha)
      errors.confirmacao_senha = 'As senhas não coincidem.';
  } else if (
    values.email_usuario.trim().toLowerCase() !== original.email_usuario &&
    !values.senha_atual
  ) {
    errors.senha_atual = 'Confirme sua senha atual para alterar o e-mail.';
  }
  if (values.tipo_cadastro === 'docente') {
    if (!values.titulacao_docente) errors.titulacao_docente = 'Selecione sua titulação.';
    const areas = parseAreas(values.areas_interesse);
    if (areas.length > 20 || areas.some((area) => area.length > 150))
      errors.areas_interesse = 'Informe até 20 áreas, com até 150 caracteres cada.';
    if (values.instituicao_origem_docente.trim().length > 200)
      errors.instituicao_origem_docente = 'Use até 200 caracteres.';
    if (values.url_lattes_docente.trim()) {
      try {
        const url = new URL(values.url_lattes_docente.trim());
        if (
          !['http:', 'https:'].includes(url.protocol) ||
          !url.hostname ||
          url.username ||
          values.url_lattes_docente.trim().length > 2048
        )
          throw new Error();
      } catch {
        errors.url_lattes_docente = 'Informe uma URL HTTP ou HTTPS válida.';
      }
    }
  } else if (!original) {
    if (!values.matricula_aluno.trim()) errors.matricula_aluno = 'Informe sua matrícula.';
    else if (values.matricula_aluno.trim().length > 30)
      errors.matricula_aluno = 'Use até 30 caracteres.';
    if (!values.id_curso) errors.id_curso = 'Selecione seu curso.';
  }
  return errors;
}

export function payload(values: FormValues, original?: User) {
  const result: Record<string, unknown> = { nome_usuario: values.nome_usuario.trim() };
  const email = values.email_usuario.trim().toLowerCase();
  if (!original || email !== original.email_usuario) result.email_usuario = email;
  if (original && email !== original.email_usuario) result.senha_atual = values.senha_atual;
  if (!original) {
    result.senha = values.senha;
    result.tipo_cadastro = values.tipo_cadastro;
  }
  if (values.tipo_cadastro === 'docente') {
    Object.assign(result, {
      titulacao_docente: values.titulacao_docente,
      areas_interesse: parseAreas(values.areas_interesse),
      url_lattes_docente: values.url_lattes_docente.trim() || null,
      instituicao_origem_docente: values.instituicao_origem_docente.trim() || null,
    });
    if (!original) result.tipo_docente = values.tipo_docente;
  } else if (!original) {
    result.matricula_aluno = values.matricula_aluno.trim();
    result.id_curso = Number(values.id_curso);
  }
  return result;
}
