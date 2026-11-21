import type { User } from './types';

/**
 * Páginas da área acadêmica e quem pode usá-las (CR-2026-0004 — barra lateral por perfil).
 *
 * As regras espelham as verificações do backend, que continua sendo a fonte de verdade:
 * aqui só se decide o que aparece no menu e para onde levar quem digita um endereço proibido.
 */
export type AcademicPage =
  | 'perfil'
  | 'turmas'
  | 'matriculas'
  | 'trabalhos'
  | 'reunioes'
  | 'monitoramento'
  | 'organizar-defesas'
  | 'bancas'
  | 'documentos'
  | 'manuscrito-banca';

type Access = Pick<User, 'perfis' | 'professor' | 'estudante'>;

const isStudent = (user: Access) => user.perfis.includes('estudante') || !!user.estudante;
const isTeacher = (user: Access) => !!user.professor;
/** Professor da disciplina ou coordenador com vínculo interno (backend: classes.manager). */
const isCourseStaff = (user: Access) =>
  user.professor?.tipo_professor === 'interno' &&
  user.perfis.some((profile) => profile === 'professor_disciplina' || profile === 'coordenador');

const RULES: Record<AcademicPage, (user: Access) => boolean> = {
  perfil: () => true,
  turmas: isCourseStaff,
  // Estudante faz autoinscrição; a equipe da disciplina gerencia as matrículas.
  matriculas: (user) => isStudent(user) || isCourseStaff(user),
  // Estudante cadastra o trabalho; docentes respondem aos convites de orientação.
  trabalhos: (user) => isStudent(user) || isTeacher(user),
  // Estudante, orientador (docente com orientação aceita) e equipe da disciplina.
  reunioes: (user) => isStudent(user) || isTeacher(user),
  monitoramento: isCourseStaff,
  'organizar-defesas': isCourseStaff,
  bancas: isTeacher,
  documentos: isStudent,
  // Aberto pelo link do e-mail da banca; o backend confere estudante, membro ou equipe.
  'manuscrito-banca': () => true,
};

export function canAccess(page: AcademicPage, user: Access): boolean {
  return RULES[page](user);
}
