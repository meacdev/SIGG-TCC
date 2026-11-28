import { describe, expect, it } from 'vitest';
import { canAccess, type AcademicPage } from './navigation';
import type { Teacher, User } from './types';

const MENU: AcademicPage[] = [
  'perfil',
  'turmas',
  'matriculas',
  'trabalhos',
  'reunioes',
  'monitoramento',
  'organizar-defesas',
  'bancas',
  'documentos',
  'usuarios',
];

const teacher = (tipo: Teacher['tipo_professor'] = 'interno'): Teacher => ({
  tipo_professor: tipo,
  titulacao_professor: 'Doutor',
  areas_interesse: [],
  url_lattes_professor: null,
  instituicao_origem_professor: null,
});

type Access = Pick<User, 'perfis' | 'professor' | 'estudante'>;
const visible = (user: Access) => MENU.filter((page) => canAccess(page, user));

describe('barra lateral por perfil (CR-2026-0004)', () => {
  it('estudante não vê turmas, monitoramento, defesas nem bancas', () => {
    const user = { perfis: ['estudante'], estudante: { matricula_estudante: '1', id_curso: 1 } };
    expect(visible(user)).toEqual(['perfil', 'matriculas', 'trabalhos', 'reunioes', 'documentos']);
  });

  it('professor sem perfil de gestão não vê Minhas atas nem as telas da disciplina', () => {
    const user = { perfis: [], professor: teacher() };
    expect(visible(user)).toEqual(['perfil', 'trabalhos', 'reunioes', 'bancas']);
  });

  it('professor da disciplina vê as telas de gestão da turma', () => {
    const user = { perfis: ['professor_disciplina'], professor: teacher() };
    expect(visible(user)).toEqual([
      'perfil',
      'turmas',
      'matriculas',
      'trabalhos',
      'reunioes',
      'monitoramento',
      'organizar-defesas',
      'bancas',
    ]);
  });

  it('coordenador tem o mesmo menu do professor da disciplina', () => {
    const coordinator = { perfis: ['coordenador'], professor: teacher() };
    const subject = { perfis: ['professor_disciplina'], professor: teacher() };
    expect(visible(coordinator)).toEqual(visible(subject));
  });

  it('avaliador externo vê só cadastro, orientações, reuniões e bancas', () => {
    const user = { perfis: ['avaliador', 'professor_disciplina'], professor: teacher('externo') };
    expect(visible(user)).toEqual(['perfil', 'trabalhos', 'reunioes', 'bancas']);
  });

  it('conta sem vínculo acadêmico vê apenas Meu cadastro', () => {
    expect(visible({ perfis: [] })).toEqual(['perfil']);
  });

  it('administrador vê a gestão de usuários; os demais perfis não', () => {
    expect(visible({ perfis: ['administrador'] })).toEqual(['perfil', 'usuarios']);
    const coordinator = { perfis: ['coordenador', 'administrador'], professor: teacher() };
    expect(visible(coordinator)).toContain('usuarios');
    expect(canAccess('usuarios', { perfis: ['coordenador'], professor: teacher() })).toBe(false);
  });

  it('manuscrito da banca continua acessível pelo link do e-mail', () => {
    expect(canAccess('manuscrito-banca', { perfis: [] })).toBe(true);
  });
});
