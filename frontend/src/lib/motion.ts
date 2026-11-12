// Valores de movimento espelhando os tokens CSS (RUI-05, RUI-12). Use sempre estes, nunca números soltos.
export const dur = { fast: 0.15, base: 0.22, slow: 0.32, slower: 0.4, pulse: 1.6 } as const;
export const ease = {
  out: [0.22, 1, 0.36, 1] as [number, number, number, number],
  inOut: [0.65, 0, 0.35, 1] as [number, number, number, number],
};
export const stagger = 0.04;

export const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: dur.base, ease: ease.out } },
};
export const fadeOnly = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: dur.base, ease: ease.out } },
};
