-- 008-comentarios: sugestões de comentário para posts de outras pessoas.
CREATE TABLE comentarios (
  id INTEGER PRIMARY KEY,
  autor TEXT NOT NULL DEFAULT '',
  link TEXT NOT NULL DEFAULT '',
  texto_post TEXT NOT NULL DEFAULT '',
  imagens TEXT NOT NULL DEFAULT '[]',
  parametros TEXT NOT NULL DEFAULT '{}',
  instrucoes TEXT NOT NULL DEFAULT '',
  resumo_post TEXT NOT NULL DEFAULT '',
  sugestoes TEXT NOT NULL DEFAULT '[]',
  prompt TEXT,
  resposta_bruta TEXT,
  erro TEXT,
  criado_em TEXT NOT NULL,
  gerado_em TEXT
);
CREATE INDEX ix_comentarios_criado ON comentarios(criado_em DESC);
