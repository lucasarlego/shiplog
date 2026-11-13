-- Cada versão de post/artigo guarda os parâmetros e as instruções extras com que foi escrita, venha ela da
-- geração pela interface (copiados da geração) ou do Claude Code pelo MCP (enviados no save_*).
ALTER TABLE posts ADD COLUMN parametros TEXT NOT NULL DEFAULT '{}';
ALTER TABLE posts ADD COLUMN instrucoes_extras TEXT NOT NULL DEFAULT '';
ALTER TABLE artigos ADD COLUMN parametros TEXT NOT NULL DEFAULT '{}';
ALTER TABLE artigos ADD COLUMN instrucoes_extras TEXT NOT NULL DEFAULT '';

UPDATE posts SET
  parametros = COALESCE((SELECT g.parametros FROM geracoes g WHERE g.id = posts.geracao_id), '{}'),
  instrucoes_extras = COALESCE((SELECT g.instrucoes_extras FROM geracoes g WHERE g.id = posts.geracao_id), '')
WHERE geracao_id IS NOT NULL;
UPDATE artigos SET
  parametros = COALESCE((SELECT g.parametros FROM geracoes g WHERE g.id = artigos.geracao_id), '{}'),
  instrucoes_extras = COALESCE((SELECT g.instrucoes_extras FROM geracoes g WHERE g.id = artigos.geracao_id), '')
WHERE geracao_id IS NOT NULL;
