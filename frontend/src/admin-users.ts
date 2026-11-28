import type { Title } from './types';
import { digits, formatCpf, validCpf, validEmail, validPhone } from './validation';

/** UC14 Manter Usuários: contrato de `/admin/usuarios` (ver docs/UC14.md). */
export type Situation = 'ativo' | 'pendente' | 'inativo';
export type Kind = 'estudante' | 'docente' | 'administrativo';
export type CourseProfile = 'professor_disciplina' | 'coordenador';
export type ManagedProfile = 'administrador' | CourseProfile;

export interface Grant {
  codigo_perfil: string;
  data_concessao: string;
  data_expiracao: string | null;
}
export interface CourseLink {
  id_curso: number;
  nome_curso: string;
  professor_disciplina: boolean;
  coordenador: boolean;
  departamento_unidade: string | null;
  data_inicio: string;
  data_fim: string | null;
}
export interface ManagedUser {
  id_usuario: number;
  nome_usuario: string;
  email_usuario: string;
  cpf_usuario: string | null;
  telefone_usuario: string | null;
  ativo_usuario: boolean;
  situacao_conta: Situation;
  tipo_cadastro: Kind;
  data_criacao_usuario: string;
  data_atualizacao_usuario: string;
  perfis: string[];
  concessoes: Grant[];
  vinculos_curso: CourseLink[];
  data_expiracao_convite: string | null;
  /** Só na resposta da alteração: novo e-mail aguardando confirmação. */
  alteracao_email?: { novo_email: string; enviado: boolean | null } | null;
  estudante?: { matricula_estudante: string; id_curso: number };
  professor?: {
    tipo_professor: 'interno' | 'externo';
    titulacao_professor: Title;
    instituicao_origem_professor: string | null;
    ativo_professor: boolean;
  };
}
/** Vínculos que impedem a inativação (RN 10), devolvidos com `UC_14_M12`. */
export interface Blocker {
  tipo: 'turma' | 'orientacao' | 'banca';
  id: number;
  descricao: string;
}

export const INSTITUTIONAL_DOMAIN = 'uea.edu.br';

export const SITUATION_LABELS: Record<Situation, string> = {
  ativo: 'Ativa',
  pendente: 'Convite pendente',
  inativo: 'Inativa',
};
export const KIND_LABELS: Record<Kind, string> = {
  estudante: 'Estudante',
  docente: 'Docente',
  administrativo: 'Administrativo',
};
export const PROFILE_LABELS: Record<string, string> = {
  administrador: 'Administrador(a)',
  coordenador: 'Coordenador(a) de curso',
  professor_disciplina: 'Professor(a) da disciplina',
  orientador: 'Orientador(a)',
  avaliador: 'Membro de banca',
  estudante: 'Estudante',
};
export const profileLabel = (code: string) => PROFILE_LABELS[code] || code;
/** Perfis concedidos aqui; orientador, avaliador e estudante nascem dos fluxos acadêmicos (RN 06). */
export const MANAGED_PROFILES: ManagedProfile[] = [
  'professor_disciplina',
  'coordenador',
  'administrador',
];
export const COURSE_PROFILES: CourseProfile[] = ['professor_disciplina', 'coordenador'];
export const isCourseProfile = (code: string): code is CourseProfile =>
  (COURSE_PROFILES as string[]).includes(code);
export const BLOCKER_LABELS: Record<Blocker['tipo'], string> = {
  turma: 'Turma ativa',
  orientacao: 'Orientação em andamento',
  banca: 'Banca agendada',
};

export interface UserValues {
  nome_usuario: string;
  email_usuario: string;
  cpf_usuario: string;
  telefone_usuario: string;
  tipo_cadastro: Kind;
  matricula_estudante: string;
  id_curso: string;
  tipo_professor: 'interno' | 'externo';
  titulacao_professor: Title | '';
  instituicao_origem_professor: string;
}
export type UserErrors = Partial<Record<keyof UserValues, string>>;

export const emptyUser: UserValues = {
  nome_usuario: '',
  email_usuario: '',
  cpf_usuario: '',
  telefone_usuario: '',
  tipo_cadastro: 'estudante',
  matricula_estudante: '',
  id_curso: '',
  tipo_professor: 'interno',
  titulacao_professor: '',
  instituicao_origem_professor: '',
};

export function valuesFrom(user: ManagedUser): UserValues {
  return {
    nome_usuario: user.nome_usuario,
    email_usuario: user.email_usuario,
    cpf_usuario: formatCpf(user.cpf_usuario),
    telefone_usuario: user.telefone_usuario || '',
    tipo_cadastro: user.tipo_cadastro,
    matricula_estudante: user.estudante?.matricula_estudante || '',
    id_curso: String(user.estudante?.id_curso || ''),
    tipo_professor: user.professor?.tipo_professor || 'interno',
    titulacao_professor: user.professor?.titulacao_professor || '',
    instituicao_origem_professor: user.professor?.instituicao_origem_professor || '',
  };
}

const external = (values: UserValues) =>
  values.tipo_cadastro === 'docente' && values.tipo_professor === 'externo';
export const institutional = (email: string) =>
  email.trim().toLowerCase().endsWith(`@${INSTITUTIONAL_DOMAIN}`);

/** Espelha as regras do backend para avisar antes do envio; o servidor continua decidindo. */
export function validateUser(values: UserValues, original?: ManagedUser): UserErrors {
  const errors: UserErrors = {};
  const name = values.nome_usuario.trim();
  if (!name) errors.nome_usuario = 'Obrigatório.';
  else if (name.length < 3 || name.length > 100) errors.nome_usuario = 'Use de 3 a 100 caracteres.';
  const email = values.email_usuario.trim().toLowerCase();
  const emailChanged = !original || email !== original.email_usuario;
  const becameInternal =
    original?.professor?.tipo_professor === 'externo' && values.tipo_professor === 'interno';
  if (!email) errors.email_usuario = 'Obrigatório.';
  else if (!validEmail(email) || email.length > 254)
    errors.email_usuario = 'Informe um endereço de e-mail válido.';
  // Contas antigas mantêm o e-mail até ele mudar ou o docente externo virar interno.
  else if ((emailChanged || becameInternal) && !external(values) && !institutional(email))
    errors.email_usuario = `Use um e-mail @${INSTITUTIONAL_DOMAIN}.`;
  if (values.cpf_usuario.trim() && !validCpf(values.cpf_usuario))
    errors.cpf_usuario = 'Informe um CPF válido.';
  if (values.telefone_usuario.trim() && !validPhone(values.telefone_usuario))
    errors.telefone_usuario = 'Informe um telefone válido com DDD.';
  if (values.tipo_cadastro === 'estudante') {
    const enrollment = values.matricula_estudante.trim();
    if (!enrollment) errors.matricula_estudante = 'Obrigatório.';
    else if (enrollment.length > 30) errors.matricula_estudante = 'Use até 30 caracteres.';
    if (!values.id_curso) errors.id_curso = 'Obrigatório.';
  }
  if (values.tipo_cadastro === 'docente') {
    if (!values.titulacao_professor) errors.titulacao_professor = 'Obrigatório.';
    const institution = values.instituicao_origem_professor.trim();
    if (institution.length > 200) errors.instituicao_origem_professor = 'Use até 200 caracteres.';
    else if (values.tipo_professor === 'externo' && !institution)
      errors.instituicao_origem_professor = 'Obrigatório para professor externo.';
  }
  return errors;
}

/** Pré-cadastro envia o tipo; a edição envia só o que mudou (null limpa campos opcionais). */
export function userPayload(values: UserValues, original?: ManagedUser) {
  const result: Record<string, unknown> = {};
  const set = (field: string, value: unknown, previous: unknown) => {
    if (!original || value !== previous) result[field] = value;
  };
  set('nome_usuario', values.nome_usuario.trim(), original?.nome_usuario);
  set('email_usuario', values.email_usuario.trim().toLowerCase(), original?.email_usuario);
  for (const field of ['cpf_usuario', 'telefone_usuario'] as const) {
    const value = digits(values[field]) || null;
    if (original ? value !== original[field] : value) result[field] = value;
  }
  if (!original) result.tipo_cadastro = values.tipo_cadastro;
  if (values.tipo_cadastro === 'estudante') {
    set(
      'matricula_estudante',
      values.matricula_estudante.trim(),
      original?.estudante?.matricula_estudante,
    );
    set('id_curso', Number(values.id_curso), original?.estudante?.id_curso);
  }
  if (values.tipo_cadastro === 'docente') {
    const teacher = original?.professor;
    set('tipo_professor', values.tipo_professor, teacher?.tipo_professor);
    set('titulacao_professor', values.titulacao_professor, teacher?.titulacao_professor);
    const institution = values.instituicao_origem_professor.trim() || null;
    if (original ? institution !== (teacher?.instituicao_origem_professor ?? null) : institution)
      result.instituicao_origem_professor = institution;
  }
  return result;
}

/** Data escolhida no formulário vale até o fim do dia no horário de Manaus (UTC-4). */
export const endOfDay = (date: string) => (date ? `${date}T23:59:59-04:00` : null);

export const formatDate = (value: string | null, withTime = false) =>
  value
    ? new Intl.DateTimeFormat('pt-BR', {
        dateStyle: 'short',
        ...(withTime ? { timeStyle: 'short' } : {}),
        timeZone: 'America/Manaus',
      }).format(new Date(value))
    : '';

/** Datas sem horário (AAAA-MM-DD) não passam por fuso, para não voltar um dia. */
export const formatDay = (value: string | null) =>
  value ? value.slice(0, 10).split('-').reverse().join('/') : '';
