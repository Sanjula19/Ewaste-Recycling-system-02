import React from 'react';
import { materialColorVar, materialLabel } from '../utils/materials.js';
import { useLanguage } from '../context/LanguageContext.jsx';

export default function MaterialChip({ materialKey, label }) {
  const { t } = useLanguage();
  return (
    <span className="material-chip" style={{ '--chip-color': materialColorVar(materialKey) }}>
      {label || materialLabel(materialKey, t)}
    </span>
  );
}
