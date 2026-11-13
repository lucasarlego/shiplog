-- 009-mcp-local: projetos locais (sem remoto), versões escritas pelo Claude Code e status de comentários.
CREATE TABLE projetos_novo (
  id INTEGER PRIMARY KEY,
  origem TEXT NOT NULL DEFAULT 'repo' CHECK (origem IN ('repo','livre','local')),
  nome TEXT NOT NULL,
  descricao TEXT NOT NULL DEFAULT '',
  url_repo TEXT,
  url_normalizada TEXT UNIQUE,
  branch TEXT,
  caminho_local TEXT,
  notas TEXT NOT NULL DEFAULT '',
  arquivado INTEGER NOT NULL DEFAULT 0,
  commit_remoto TEXT,
  verificado_em TEXT,
  criado_em TEXT NOT NULL,
  ultima_analise_em TEXT
);

INSERT INTO projetos_novo (id, origem, nome, descricao, url_repo, url_normalizada, branch, caminho_local, notas,
                           arquivado, commit_remoto, verificado_em, criado_em, ultima_analise_em)
SELECT id, origem, nome, descricao, url_repo, url_normalizada, branch, caminho_local, notas,
       arquivado, commit_remoto, verificado_em, criado_em, ultima_analise_em
FROM projetos;

DROP TABLE projetos;
ALTER TABLE projetos_novo RENAME TO projetos;
CREATE INDEX ix_projetos_origem ON projetos(origem);
CREATE UNIQUE INDEX ux_projetos_local ON projetos(caminho_local) WHERE origem = 'local';

ALTER TABLE posts ADD COLUMN fonte TEXT NOT NULL DEFAULT 'shiplog';
ALTER TABLE posts ADD COLUMN commit_referencia TEXT;
ALTER TABLE artigos ADD COLUMN fonte TEXT NOT NULL DEFAULT 'shiplog';
ALTER TABLE artigos ADD COLUMN commit_referencia TEXT;

ALTER TABLE comentarios ADD COLUMN plataforma TEXT NOT NULL DEFAULT 'linkedin';
ALTER TABLE comentarios ADD COLUMN status TEXT NOT NULL DEFAULT 'sugerido';
ALTER TABLE comentarios ADD COLUMN escolhido INTEGER;
ALTER TABLE comentarios ADD COLUMN texto_final TEXT;
ALTER TABLE comentarios ADD COLUMN link_publicado TEXT;
ALTER TABLE comentarios ADD COLUMN fonte TEXT NOT NULL DEFAULT 'shiplog';
