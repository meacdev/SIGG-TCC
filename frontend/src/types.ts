export type Title = 'Especialista' | 'Mestre' | 'Doutor';
export interface Teacher {
  tipo_professor: 'interno' | 'externo';
  titulacao_professor: Title;
  areas_interesse: string[];
  url_lattes_professor: string | null;
  instituicao_origem_professor: string | null;
}
export interface User {
  id_usuario: number;
  nome_usuario: string;
  email_usuario: string;
  cpf_usuario: string | null;
  telefone_usuario: string | null;
  ativo_usuario: boolean;
  data_criacao_usuario: string;
  data_atualizacao_usuario: string;
  perfis: string[];
  professor?: Teacher;
  estudante?: { matricula_estudante: string; id_curso: number };
}
export interface Course {
  id_curso: number;
  nome_curso: string;
  codigo_curso: string;
}
export interface Tokens {
  access_token: string;
  refresh_token: string;
  usuario?: User;
}
export interface Envelope<T> {
  data: T;
  code?: string;
  message?: string;
  meta?: { pages: number };
}
export interface FormValues {
  nome_usuario: string;
  email_usuario: string;
  senha: string;
  confirmacao_senha: string;
  cpf_usuario: string;
  telefone_usuario: string;
  tipo_cadastro: 'professor' | 'estudante';
  titulacao_professor: Title | '';
  tipo_professor: 'interno' | 'externo';
  instituicao_origem_professor: string;
  areas_interesse: string;
  url_lattes_professor: string;
  matricula_estudante: string;
  id_curso: string;
  senha_atual: string;
}
export type FieldErrors = Partial<Record<keyof FormValues, string>>;
