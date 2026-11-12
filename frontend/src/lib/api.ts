import type { ApiErro, Artigo, Comentario, Config, Debug, Health, Job, Projeto, Post, TipoGeracao } from "./types";

export class ApiError extends Error {
  constructor(public erro: ApiErro, public status: number) {
    super(erro.mensagem);
  }
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${url}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      { codigo: "rede", mensagem: "Não foi possível falar com o servidor local.", acao_sugerida: "Verifique se o Shiplog está rodando." },
      0,
    );
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(
      data?.erro ?? { codigo: "erro_interno", mensagem: `Erro ${res.status}`, acao_sugerida: null },
      res.status,
    );
  }
  return data as T;
}

export const api = {
  health: () => req<Health>("GET", "/health"),
  healthRefresh: () => req<Health>("POST", "/health/refresh"),

  projetos: (status?: string) => req<Projeto[]>("GET", `/projects${status ? `?status=${status}` : ""}`),
  projeto: (id: number) => req<Projeto>("GET", `/projects/${id}`),
  validarUrl: (url: string) =>
    req<{ valida: boolean; nome_sugerido: string | null; erro: ApiErro | null }>("POST", "/projects/validate", { url }),
  criarProjeto: (body: { url?: string; descricao?: string; nome?: string; branch?: string; notas?: string; gerar?: boolean; parametros?: object }) =>
    req<{ projeto: Projeto; job: Job | null; aviso: ApiErro | null }>("POST", "/projects", body),
  editarProjeto: (id: number, body: { nome?: string; branch?: string; notas?: string; descricao?: string }) =>
    req<Projeto>("PATCH", `/projects/${id}`, body),
  excluirProjeto: (id: number, manterHistorico: boolean) =>
    req<void>("DELETE", `/projects/${id}?manter_historico=${manterHistorico}`),
  checkUpdates: () => req<{ id: number; commits_novos: boolean }[]>("POST", "/projects/check-updates", {}),

  gerar: (
    projetoId: number,
    body: {
      tipo: TipoGeracao;
      parametros?: object;
      instrucoes_extras?: string;
      base_versao_id?: number | null;
      atualizar_repo?: boolean;
      atualizacao?: boolean;
    },
  ) => req<Job>("POST", `/projects/${projetoId}/generations`, body),
  geracoes: (projetoId: number) => req<Job[]>("GET", `/projects/${projetoId}/generations`),
  jobsAtivos: () => req<Job[]>("GET", "/jobs?ativos=true"),
  job: (id: number) => req<Job>("GET", `/jobs/${id}`),
  cancelar: (id: number) => req<Job>("POST", `/jobs/${id}/cancel`),
  retry: (id: number) => req<Job>("POST", `/jobs/${id}/retry`),
  debug: (id: number) => req<Debug>("GET", `/generations/${id}/debug`),

  posts: (projetoId: number) => req<Post[]>("GET", `/projects/${projetoId}/posts`),
  salvarPost: (id: number, body: { texto: string; hashtags?: string[] }) => req<Post>("POST", `/posts/${id}/versions`, body),
  statusPost: (id: number, status: string, link?: string | null) =>
    req<Post>("PATCH", `/posts/${id}/status`, { status, link: link || null }),

  artigos: (projetoId: number) => req<Artigo[]>("GET", `/projects/${projetoId}/articles`),
  salvarArtigo: (id: number, body: { titulo: string; subtitulo: string; corpo_markdown: string; tags: string[] }) =>
    req<Artigo>("POST", `/articles/${id}/versions`, body),
  statusArtigo: (id: number, status: string, link?: string | null) =>
    req<Artigo>("PATCH", `/articles/${id}/status`, { status, link: link || null }),
  exportArtigoUrl: (id: number) => `/api/articles/${id}/export.md`,

  config: () => req<Config>("GET", "/settings"),
  salvarConfig: (body: Partial<Config>) => req<Config>("PUT", "/settings", body),
  enviarCurriculo: (nome: string, conteudo_base64: string) => req<Config>("PUT", "/profile/curriculo", { nome, conteudo_base64 }),
  removerCurriculo: () => req<Config>("DELETE", "/profile/curriculo"),
  gerarPerfil: (sobre: string) => req<Config>("POST", "/profile/generate", { sobre }),

  comentarios: () => req<Comentario[]>("GET", "/comments"),
  comentario: (id: number) => req<Comentario>("GET", `/comments/${id}`),
  criarComentario: (body: { autor?: string; link?: string; texto_post: string; imagens: { nome: string; conteudo_base64: string }[] }) =>
    req<Comentario>("POST", "/comments", body),
  gerarComentario: (id: number, body: { parametros?: Record<string, string>; instrucoes?: string }) =>
    req<Comentario>("POST", `/comments/${id}/generate`, body),
  excluirComentario: (id: number) => req<void>("DELETE", `/comments/${id}`),
  imagemComentario: (id: number, nome: string) => `/api/comments/${id}/images/${encodeURIComponent(nome)}`,
  exportUrl: (formato: "md" | "json") => `/api/export?formato=${formato}`,
};
