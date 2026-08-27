/*
  Single source of truth mapping each material to its identity color
  (CSS variable defined in styles/tokens.css) and its translation key.
  Used by the Forecast/Disposition dropdowns, MaterialChip, and the
  Manifest table, so a given material always reads the same color and
  the same label everywhere in the app.
*/

export const METALS = [
  { key: 'aluminium', cssVar: '--mat-aluminium', i18nKey: 'metals.aluminium' },
  { key: 'copper', cssVar: '--mat-copper', i18nKey: 'metals.copper' },
  { key: 'lead', cssVar: '--mat-lead', i18nKey: 'metals.lead' },
  { key: 'nickel', cssVar: '--mat-nickel', i18nKey: 'metals.nickel' },
  { key: 'steel', cssVar: '--mat-steel', i18nKey: 'metals.steel' },
  { key: 'zinc', cssVar: '--mat-zinc', i18nKey: 'metals.zinc' },
];

export const RESIDUALS = [
  { key: 'PVC Plastic', cssVar: '--mat-pvc', i18nKey: 'materials.pvc plastic' },
  { key: 'Polystyrene', cssVar: '--mat-polystyrene', i18nKey: 'materials.polystyrene' },
  { key: 'Contaminated Glass', cssVar: '--mat-glass', i18nKey: 'materials.contaminated glass' },
];

const ALL = [...METALS, ...RESIDUALS];

/** Finds a material's CSS color variable by its key, case-insensitively. */
export function materialColorVar(key) {
  const found = ALL.find((m) => m.key.toLowerCase() === String(key).toLowerCase());
  return found ? `var(${found.cssVar})` : 'var(--color-text-faint)';
}

/** Finds a material's translated label given the current t() function. */
export function materialLabel(key, t) {
  const found = ALL.find((m) => m.key.toLowerCase() === String(key).toLowerCase());
  return found ? t(found.i18nKey) : key;
}
