-- 006-post-sem-repositorio: projetos podem nascer de uma descrição livre (sem repositório).
-- SQLite não remove NOT NULL via ALTER TABLE: recria a tabela preservando os dados.
CREATE TABLE projetos_novo (
  id INTEGER PRIMARY KEY,
  origem TEXT NOT NULL DEFAULT 'repo' CHECK (origem IN ('repo','livre')),
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
SELECT id, 'repo', nome, '', url_repo, url_normalizada, branch, caminho_local, notas,
       arquivado, commit_remoto, verificado_em, criado_em, ultima_analise_em
FROM projetos;

DROP TABLE projetos;
ALTER TABLE projetos_novo RENAME TO projetos;
CREATE INDEX ix_projetos_origem ON projetos(origem);
