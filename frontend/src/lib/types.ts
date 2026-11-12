// Espelho dos contratos da API (spec 004).
export type StatusVersao = "rascunho" | "pronto" | "publicado";
export type StatusJob = "na_fila" | "clonando" | "analisando" | "gerando" | "concluido" | "erro" | "cancelado";
export type TipoGeracao = "post" | "artigo";

export interface ApiErro {
  codigo: string;
  mensagem: string;
  acao_sugerida: string | null;
  detalhes?: Record<string, unknown>;
}

export interface MiniVersao { id: number; versao: number; status: StatusVersao; criado_em: string }

export type OrigemProjeto = "repo" | "livre";

export interface Projeto {
  id: number;
  origem: OrigemProjeto;
  descricao: string;
  nome: string;
  url_repo: string | null;
  branch: string | null;
  notas: string;
  arquivado: boolean;
  criado_em: string;
  ultima_analise_em: string | null;
  commit_analisado: string | null;
  commit_remoto: string | null;
  commits_novos: boolean;
  ultimo_post: MiniVersao | null;
  ultimo_artigo: MiniVersao | null;
  artigo_publicado: { id: number; titulo: string; link: string | null } | null;
  job_ativo: { id: number; tipo: TipoGeracao; status: StatusJob } | null;
  caminho_local?: string | null;
  clone_existe?: boolean;
  rodada_atual?: number;
}

export interface Job {
  id: number;
  projeto_id: number;
  tipo: TipoGeracao;
  status: StatusJob;
  posicao_fila: number;
  parametros: Record<string, unknown>;
  instrucoes_extras: string;
  commit_hash: string | null;
  erro: string | null;
  erro_codigo: string | null;
  acao_sugerida: string | null;
  avisos: string[];
  resultado_id: number | null;
  tentativas: number;
  duracao_ms: number | null;
  criado_em: string;
  iniciado_em: string | null;
  finalizado_em: string | null;
}

interface VersaoBase {
  id: number;
  projeto_id: number;
  geracao_id: number | null;
  versao: number;
  rodada: number;
  origem_id: number | null;
  status: StatusVersao;
  publicado_em: string | null;
  link: string | null;
  editado_manualmente: boolean;
  instrucoes_extras: string;
  parametros: Record<string, unknown>;
  commit_hash: string | null;
  criado_em: string;
}

export interface Post extends VersaoBase {
  texto: string;
  hooks_alternativos: string[];
  hashtags: string[];
  resumo_tecnico: string;
  destaques: string[];
}

export interface Artigo extends VersaoBase {
  titulo: string;
  subtitulo: string;
  corpo_markdown: string;
  tags: string[];
  trechos_de_codigo: { arquivo: string; linhas: string }[];
  sugestoes_de_imagens: string[];
}

export interface CheckItem { ok: boolean; mensagem: string | null; comando_sugerido?: string | null }
export interface Health {
  cli: CheckItem & { caminho: string | null; versao: string | null };
  auth: CheckItem & { metodo?: string; plano?: string };
  skill: CheckItem;
  git: CheckItem & { versao: string | null };
  pode_gerar_post: boolean;
  pode_gerar_artigo: boolean;
  verificado_em: string;
}

export interface ParamsPost { tom: string; tamanho: string; idioma: string; incluir_link_artigo?: boolean }
export interface ParamsArtigo { idioma: string; publico: string; formato: string }

export interface Config {
  prompt_base: string;
  perfil_voz: string;
  perfil_profissional: string;
  perfil_sobre: string;
  curriculo_nome: string;
  perfil_gerado_em: string | null;
  pasta_dados: string;
  caminho_cli: string;
  timeout_post_s: number;
  timeout_artigo_s: number;
  modelo: string;
  parametros_padrao_post: ParamsPost;
  parametros_padrao_artigo: ParamsArtigo;
  reinicio_necessario: boolean;
}

export interface Debug {
  id: number;
  prompt: string | null;
  resposta_bruta: string | null;
  duracao_ms: number | null;
  codigo_saida: number | null;
  tentativas: number;
  erro: string | null;
  erro_codigo: string | null;
  status: StatusJob;
}

// Spec 008 — comentários em posts de outras pessoas.
export interface SugestaoComentario { abordagem: string; texto: string }
export interface Comentario {
  id: number;
  autor: string;
  link: string;
  texto_post: string;
  imagens: string[];
  parametros: { objetivo?: string; tamanho?: string; idioma?: string };
  instrucoes: string;
  resumo_post: string;
  sugestoes: SugestaoComentario[];
  erro: string | null;
  criado_em: string;
  gerado_em: string | null;
}
