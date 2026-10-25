import { describe, expect, it } from 'vitest';
import { emptyForm, fromUser, payload, validate } from './validation';
import type { FormValues, User } from './types';

const teacher: FormValues = {
  ...emptyForm,
  tipo_cadastro: 'docente',
  nome_usuario: ' Maria Silva ',
  email_usuario: ' Maria@Example.com ',
  senha: 'Senha de teste 123',
  confirmacao_senha: 'Senha de teste 123',
  titulacao_docente: 'mestre',
};

describe('regras do cadastro', () => {
  it('aceita docente sem áreas, Lattes ou instituição', () => {
    expect(validate(teacher)).toEqual({});
    expect(payload(teacher)).toMatchObject({
      nome_usuario: 'Maria Silva',
      email_usuario: 'maria@example.com',
      areas_interesse: [],
      url_lattes_docente: null,
    });
  });
  it('exige os campos obrigatórios e mascara a validação de espaços', () => {
    expect(
      validate({ ...teacher, nome_usuario: ' ', titulacao_docente: '', senha: '            ' }),
    ).toMatchObject({
      nome_usuario: expect.any(String),
      titulacao_docente: expect.any(String),
      senha: expect.any(String),
    });
  });
  it('não envia dados docentes para estudante e preserva zeros da matrícula', () => {
    const values = {
      ...teacher,
      tipo_cadastro: 'aluno' as const,
      matricula_aluno: '00001234',
      id_curso: '9',
    };
    expect(validate(values)).toEqual({});
    expect(payload(values)).toEqual({
      nome_usuario: 'Maria Silva',
      email_usuario: 'maria@example.com',
      senha: teacher.senha,
      tipo_cadastro: 'aluno',
      matricula_aluno: '00001234',
      id_curso: 9,
    });
  });
  it('rejeita URL insegura, áreas excessivas e senhas diferentes', () => {
    expect(
      validate({
        ...teacher,
        url_lattes_docente: 'javascript:alert(1)',
        areas_interesse: Array.from({ length: 21 }, (_, i) => `Área ${i}`).join(','),
        confirmacao_senha: 'outra senha',
      }),
    ).toMatchObject({
      url_lattes_docente: expect.any(String),
      areas_interesse: expect.any(String),
      confirmacao_senha: expect.any(String),
    });
    expect(
      validate({ ...teacher, url_lattes_docente: 'https://nome:senha@exemplo.com' })
        .url_lattes_docente,
    ).toBeDefined();
  });
  it('normaliza áreas, evita duplicatas e mantém a senha como digitada', () => {
    expect(
      payload({ ...teacher, areas_interesse: ' IA, Web, IA, , ', senha: ' senha com espaços ' }),
    ).toMatchObject({ areas_interesse: ['IA', 'Web'], senha: ' senha com espaços ' });
  });
  it('exige senha atual só ao alterar e-mail e não envia campos imutáveis na edição', () => {
    const user: User = {
      id_usuario: 1,
      nome_usuario: 'Maria',
      email_usuario: 'maria@example.com',
      ativo_usuario: true,
      data_criacao_usuario: '2026-10-23T12:00:00Z',
      data_atualizacao_usuario: '2026-10-23T12:00:00Z',
      perfis: [],
      docente: {
        tipo_docente: 'interno',
        titulacao_docente: 'mestre',
        areas_interesse: [],
        url_lattes_docente: null,
        instituicao_origem_docente: null,
      },
    };
    const values = fromUser(user);
    expect(payload(values, user)).not.toHaveProperty('email_usuario');
    expect(payload(values, user)).not.toHaveProperty('tipo_docente');
    expect(payload(values, user)).not.toHaveProperty('senha');
    expect(
      validate({ ...values, email_usuario: 'nova@example.com' }, user).senha_atual,
    ).toBeDefined();
    expect(
      payload({ ...values, email_usuario: 'nova@example.com', senha_atual: 'atual' }, user),
    ).toMatchObject({ email_usuario: 'nova@example.com', senha_atual: 'atual' });
  });
});
