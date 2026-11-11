import type { FieldErrors, FormValues, User } from './types';

export const emptyForm: FormValues = {
  nome_usuario: '',
  email_usuario: '',
  senha: '',
  confirmacao_senha: '',
  tipo_cadastro: 'estudante',
  titulacao_professor: '',
  tipo_professor: 'interno',
  instituicao_origem_professor: '',
  areas_interesse: '',
  url_lattes_professor: '',
  matricula_estudante: '',
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
    tipo_cadastro: user.professor ? 'professor' : 'estudante',
    titulacao_professor: user.professor?.titulacao_professor || '',
    tipo_professor: user.professor?.tipo_professor || 'interno',
    areas_interesse: user.professor?.areas_interesse.join(', ') || '',
    url_lattes_professor: user.professor?.url_lattes_professor || '',
    instituicao_origem_professor: user.professor?.instituicao_origem_professor || '',
    matricula_estudante: user.estudante?.matricula_estudante || '',
    id_curso: String(user.estudante?.id_curso || ''),
  };
}

export function validate(values: FormValues, original?: User): FieldErrors {
  const errors: FieldErrors = {};
  // RF20.1.1 / ck_usuario_nome: 3 to 100 characters.
  if (!values.nome_usuario.trim()) errors.nome_usuario = 'Informe seu nome completo.';
  else if (values.nome_usuario.trim().length < 3 || values.nome_usuario.trim().length > 100)
    errors.nome_usuario = 'Use de 3 a 100 caracteres.';
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
  if (values.tipo_cadastro === 'professor') {
    if (!values.titulacao_professor) errors.titulacao_professor = 'Selecione sua titulação.';
    const areas = parseAreas(values.areas_interesse);
    if (areas.length > 20 || areas.some((area) => area.length > 150))
      errors.areas_interesse = 'Informe até 20 áreas, com até 150 caracteres cada.';
    if (values.instituicao_origem_professor.trim().length > 200)
      errors.instituicao_origem_professor = 'Use até 200 caracteres.';
    else if (values.tipo_professor === 'externo' && !values.instituicao_origem_professor.trim())
      errors.instituicao_origem_professor = 'Informe a instituição de origem.';
    if (values.url_lattes_professor.trim()) {
      try {
        const url = new URL(values.url_lattes_professor.trim());
        if (
          !['http:', 'https:'].includes(url.protocol) ||
          // RF20.2.2 / ck_professor_lattes: only lattes.cnpq.br links.
          url.hostname !== 'lattes.cnpq.br' ||
          url.username ||
          values.url_lattes_professor.trim().length > 2048
        )
          throw new Error();
      } catch {
        errors.url_lattes_professor = 'Informe o link do Lattes (https://lattes.cnpq.br/...).';
      }
    }
  } else if (!original) {
    if (!values.matricula_estudante.trim()) errors.matricula_estudante = 'Informe sua matrícula.';
    else if (values.matricula_estudante.trim().length > 30)
      errors.matricula_estudante = 'Use até 30 caracteres.';
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
  if (values.tipo_cadastro === 'professor') {
    Object.assign(result, {
      titulacao_professor: values.titulacao_professor,
      areas_interesse: parseAreas(values.areas_interesse),
      url_lattes_professor: values.url_lattes_professor.trim() || null,
      instituicao_origem_professor: values.instituicao_origem_professor.trim() || null,
    });
    if (!original) result.tipo_professor = values.tipo_professor;
  } else if (!original) {
    result.matricula_estudante = values.matricula_estudante.trim();
    result.id_curso = Number(values.id_curso);
  }
  return result;
}
