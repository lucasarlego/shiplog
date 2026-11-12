const rtf = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });

export function relativo(iso: string | null | undefined): string {
  if (!iso) return "nunca";
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 45) return "agora";
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  if (abs < 86400 * 30) return rtf.format(Math.round(diff / 86400), "day");
  return dataCurta(iso);
}

export function dataCurta(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

export function dataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function duracao(ms: number | null | undefined): string {
  if (!ms) return "—";
  const s = Math.round(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}min ${s % 60}s`;
}

export function textoCompletoPost(texto: string, hashtags: string[]): string {
  return hashtags.length ? `${texto.trimEnd()}\n\n${hashtags.join(" ")}` : texto;
}

export const LIMITE_LINKEDIN = 3000;
export const CORTE_VER_MAIS = 210;
