import type { FieldErrors, FormValues, User } from './types';

export const emptyForm: FormValues = {
  nome_usuario: '',
  email_usuario: '',
  senha: '',
  confirmacao_senha: '',
  cpf_usuario: '',
  telefone_usuario: '',
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

// RF21.1.1: 8 to 128 characters with an uppercase letter, a digit and a special character.
export const PASSWORD_RULE =
  'Use de 8 a 128 caracteres, com ao menos 1 letra maiúscula, 1 número e 1 caractere especial.';
export const validPassword = (value: string) =>
  value.length >= 8 &&
  value.length <= 128 &&
  /\p{Lu}/u.test(value) &&
  /\p{Nd}/u.test(value) &&
  /[^\p{L}\p{N}]/u.test(value);

export const digits = (value: string) => value.replace(/\D/g, '');

// RF20.1 / ck_usuario_cpf: 11 digits with valid check digits.
export function validCpf(value: string) {
  if (!/^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$/.test(value.trim())) return false;
  const cpf = digits(value);
  if (new Set(cpf).size === 1) return false;
  return [9, 10].every((size) => {
    const total = [...cpf.slice(0, size)].reduce(
      (sum, d, i) => sum + Number(d) * (size + 1 - i),
      0,
    );
    return ((total * 10) % 11) % 10 === Number(cpf[size]);
  });
}

export const validPhone = (value: string) =>
  /^\+?[\d\s().-]{10,30}$/.test(value.trim()) &&
  digits(value).length >= 10 &&
  digits(value).length <= 13;

export const formatCpf = (value: string | null) =>
  value && value.length === 11
    ? `${value.slice(0, 3)}.${value.slice(3, 6)}.${value.slice(6, 9)}-${value.slice(9)}`
    : value || '';

export function fromUser(user: User): FormValues {
  return {
    ...emptyForm,
    nome_usuario: user.nome_usuario,
    email_usuario: user.email_usuario,
    cpf_usuario: formatCpf(user.cpf_usuario),
    telefone_usuario: user.telefone_usuario || '',
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
  if (values.cpf_usuario.trim() && !validCpf(values.cpf_usuario))
    errors.cpf_usuario = 'Informe um CPF válido.';
  if (values.telefone_usuario.trim() && !validPhone(values.telefone_usuario))
    errors.telefone_usuario = 'Informe um telefone válido com DDD.';
  if (!original) {
    if (!validPassword(values.senha)) errors.senha = PASSWORD_RULE;
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
  for (const field of ['cpf_usuario', 'telefone_usuario'] as const) {
    const value = digits(values[field]);
    // Sign-up omits empty optional fields; editing sends only what changed (null clears it).
    if (original ? value !== (original[field] || '') : value) result[field] = value || null;
  }
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
