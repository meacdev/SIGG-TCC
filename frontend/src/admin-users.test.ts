import { describe, expect, it } from 'vitest';
import {
  emptyUser,
  endOfDay,
  formatDay,
  userPayload,
  validateUser,
  valuesFrom,
  type ManagedUser,
} from './admin-users';

const teacher = (tipo: 'interno' | 'externo', email: string): ManagedUser => ({
  id_usuario: 7,
  nome_usuario: 'Docente Antiga',
  email_usuario: email,
  cpf_usuario: null,
  telefone_usuario: null,
  ativo_usuario: true,
  situacao_conta: 'ativo',
  tipo_cadastro: 'docente',
  data_criacao_usuario: '2026-01-01T12:00:00Z',
  data_atualizacao_usuario: '2026-01-01T12:00:00Z',
  perfis: [],
  concessoes: [],
  vinculos_curso: [],
  data_expiracao_convite: null,
  professor: {
    tipo_professor: tipo,
    titulacao_professor: 'Doutor',
    instituicao_origem_professor: tipo === 'externo' ? 'UFAM' : null,
    ativo_professor: true,
  },
});

describe('UC14: regras do formulário de usuário', () => {
  it('exige e-mail @uea.edu.br, exceto para docente externo', () => {
    const student = {
      ...emptyUser,
      nome_usuario: 'Pessoa Estudante',
      email_usuario: 'pessoa@gmail.com',
      matricula_estudante: '2026001',
      id_curso: '1',
    };
    expect(validateUser(student).email_usuario).toBe('Use um e-mail @uea.edu.br.');
    expect(validateUser({ ...student, email_usuario: 'pessoa@fakeuea.edu.br' }).email_usuario).toBe(
      'Use um e-mail @uea.edu.br.',
    );
    expect(validateUser({ ...student, email_usuario: 'Pessoa@UEA.edu.br' })).toEqual({});
    const external = {
      ...emptyUser,
      nome_usuario: 'Docente Externa',
      email_usuario: 'docente@ufam.edu.br',
      tipo_cadastro: 'docente' as const,
      tipo_professor: 'externo' as const,
      titulacao_professor: 'Mestre' as const,
    };
    expect(validateUser(external)).toEqual({
      instituicao_origem_professor: 'Obrigatório para professor externo.',
    });
    expect(validateUser({ ...external, instituicao_origem_professor: 'UFAM' })).toEqual({});
  });

  it('mantém e-mail antigo até mudar o e-mail ou o docente virar interno', () => {
    const legacy = teacher('interno', 'antiga@example.com');
    expect(validateUser({ ...valuesFrom(legacy), nome_usuario: 'Nome Novo' }, legacy)).toEqual({});
    const external = teacher('externo', 'docente@ufam.edu.br');
    expect(
      validateUser({ ...valuesFrom(external), tipo_professor: 'interno' }, external).email_usuario,
    ).toBe('Use um e-mail @uea.edu.br.');
  });

  it('envia só os campos alterados e limpa opcionais com null', () => {
    const user = { ...teacher('interno', 'docente@uea.edu.br'), telefone_usuario: '92999999999' };
    expect(userPayload(valuesFrom(user), user)).toEqual({});
    expect(
      userPayload(
        { ...valuesFrom(user), telefone_usuario: '', titulacao_professor: 'Mestre' },
        user,
      ),
    ).toEqual({ telefone_usuario: null, titulacao_professor: 'Mestre' });
  });

  it('pré-cadastro envia o tipo e omite opcionais vazios', () => {
    expect(
      userPayload({
        ...emptyUser,
        nome_usuario: ' Pessoa Estudante ',
        email_usuario: 'Pessoa@UEA.edu.br',
        matricula_estudante: '0002026',
        id_curso: '3',
      }),
    ).toEqual({
      nome_usuario: 'Pessoa Estudante',
      email_usuario: 'pessoa@uea.edu.br',
      tipo_cadastro: 'estudante',
      matricula_estudante: '0002026',
      id_curso: 3,
    });
  });

  it('formata datas sem voltar um dia e expira ao fim do dia em Manaus', () => {
    expect(formatDay('2026-11-27')).toBe('27/11/2026');
    expect(endOfDay('2026-12-31')).toBe('2026-12-31T23:59:59-04:00');
    expect(endOfDay('')).toBeNull();
  });
});
