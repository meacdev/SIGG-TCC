export type Title = 'especialista' | 'mestre' | 'doutor';
export interface Teacher {
  tipo_docente: 'interno' | 'externo';
  titulacao_docente: Title;
  areas_interesse: string[];
  url_lattes_docente: string | null;
  instituicao_origem_docente: string | null;
}
export interface User {
  id_usuario: number;
  nome_usuario: string;
  email_usuario: string;
  ativo_usuario: boolean;
  data_criacao_usuario: string;
  data_atualizacao_usuario: string;
  perfis: string[];
  docente?: Teacher;
  aluno?: { matricula_aluno: string; id_curso: number };
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
  tipo_cadastro: 'docente' | 'aluno';
  titulacao_docente: Title | '';
  tipo_docente: 'interno' | 'externo';
  instituicao_origem_docente: string;
  areas_interesse: string;
  url_lattes_docente: string;
  matricula_aluno: string;
  id_curso: string;
  senha_atual: string;
}
export type FieldErrors = Partial<Record<keyof FormValues, string>>;
