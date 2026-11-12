-- 007-perfil-profissional: currículo + texto livre viram um perfil usado nos prompts de post e artigo.
ALTER TABLE configuracoes ADD COLUMN perfil_profissional TEXT NOT NULL DEFAULT '';
ALTER TABLE configuracoes ADD COLUMN perfil_sobre TEXT NOT NULL DEFAULT '';
ALTER TABLE configuracoes ADD COLUMN curriculo_nome TEXT NOT NULL DEFAULT '';
ALTER TABLE configuracoes ADD COLUMN perfil_gerado_em TEXT;
