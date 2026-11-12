CREATE TABLE projetos (
  id INTEGER PRIMARY KEY,
  nome TEXT NOT NULL,
  url_repo TEXT NOT NULL,
  url_normalizada TEXT NOT NULL UNIQUE,
  branch TEXT,                         -- NULL = branch default do remoto (RF-04)
  caminho_local TEXT NOT NULL,
  notas TEXT NOT NULL DEFAULT '',
  arquivado INTEGER NOT NULL DEFAULT 0,
  commit_remoto TEXT,                  -- último ls-remote (RF-10)
  verificado_em TEXT,
  criado_em TEXT NOT NULL,
  ultima_analise_em TEXT
);

CREATE TABLE geracoes (
  id INTEGER PRIMARY KEY,
  projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL CHECK (tipo IN ('post','artigo')),
  status TEXT NOT NULL CHECK (status IN ('na_fila','clonando','analisando','gerando','concluido','erro','cancelado')),
  commit_hash TEXT,
  parametros TEXT NOT NULL DEFAULT '{}',
  instrucoes_extras TEXT NOT NULL DEFAULT '',
  base_versao_id INTEGER,
  atualizar_repo INTEGER NOT NULL DEFAULT 1,
  atualizacao INTEGER NOT NULL DEFAULT 0,
  prompt TEXT,
  resposta_bruta TEXT,
  codigo_saida INTEGER,
  tentativas INTEGER NOT NULL DEFAULT 0,
  duracao_ms INTEGER,
  erro TEXT, erro_codigo TEXT, acao_sugerida TEXT,
  avisos TEXT NOT NULL DEFAULT '[]',
  resultado_id INTEGER,
  criado_em TEXT NOT NULL, iniciado_em TEXT, finalizado_em TEXT
);
CREATE INDEX ix_geracoes_projeto ON geracoes(projeto_id, criado_em DESC);
CREATE INDEX ix_geracoes_status ON geracoes(status);

CREATE TABLE posts (
  id INTEGER PRIMARY KEY,
  projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
  geracao_id INTEGER REFERENCES geracoes(id) ON DELETE SET NULL,
  versao INTEGER NOT NULL,
  rodada INTEGER NOT NULL DEFAULT 1,
  origem_id INTEGER,
  texto TEXT NOT NULL,
  hooks_alternativos TEXT NOT NULL DEFAULT '[]',
  hashtags TEXT NOT NULL DEFAULT '[]',
  resumo_tecnico TEXT NOT NULL DEFAULT '',
  destaques TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho','pronto','publicado')),
  publicado_em TEXT,
  link_linkedin TEXT,
  editado_manualmente INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL,
  UNIQUE (projeto_id, versao)
);
CREATE UNIQUE INDEX ux_posts_publicado ON posts(projeto_id, rodada) WHERE status = 'publicado';

CREATE TABLE artigos (
  id INTEGER PRIMARY KEY,
  projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
  geracao_id INTEGER REFERENCES geracoes(id) ON DELETE SET NULL,
  versao INTEGER NOT NULL,
  rodada INTEGER NOT NULL DEFAULT 1,
  origem_id INTEGER,
  titulo TEXT NOT NULL, subtitulo TEXT NOT NULL DEFAULT '',
  corpo_markdown TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',
  trechos_de_codigo TEXT NOT NULL DEFAULT '[]',
  sugestoes_de_imagens TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'rascunho' CHECK (status IN ('rascunho','pronto','publicado')),
  publicado_em TEXT, link_medium TEXT,
  editado_manualmente INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL,
  UNIQUE (projeto_id, versao)
);
CREATE UNIQUE INDEX ux_artigos_publicado ON artigos(projeto_id, rodada) WHERE status = 'publicado';

CREATE TABLE configuracoes (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  prompt_base TEXT NOT NULL,
  perfil_voz TEXT NOT NULL DEFAULT '',
  caminho_cli TEXT NOT NULL DEFAULT '',
  timeout_post_s INTEGER NOT NULL DEFAULT 300,
  timeout_artigo_s INTEGER NOT NULL DEFAULT 900,
  modelo TEXT NOT NULL DEFAULT '',
  parametros_padrao_post TEXT NOT NULL,
  parametros_padrao_artigo TEXT NOT NULL,
  atualizado_em TEXT NOT NULL
);
