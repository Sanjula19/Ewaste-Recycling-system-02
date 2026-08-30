import React from "react";

// ── Minimal line-icon set (Feather-style) used in the sidebar. ──
// Plain inline SVGs (no icon-library dependency) so color/size follow
// the caller via `size`/`color` props and currentColor.
const base = (size, color) => ({
  width: size, height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: color,
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
});

export const IconRecycle = ({ size = 22, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="M7 19H4.815a1.83 1.83 0 0 1-1.57-.881 1.785 1.785 0 0 1-.004-1.784L7.196 9.5" />
    <path d="M11 19h8.203a1.83 1.83 0 0 0 1.556-.89 1.784 1.784 0 0 0 0-1.775l-1.226-2.12" />
    <path d="m14 16-3 3 3 3" />
    <path d="M8.293 13.596 4.875 9.5 8.293 5.404" />
    <path d="m9.344 5.811 1.093-1.892A1.83 1.83 0 0 1 12 3a1.784 1.784 0 0 1 1.544.891l3.985 6.9" />
    <path d="m13.378 9.633 4.096.514" />
    <path d="m17.5 5.5-1 4-4-1" />
  </svg>
);

export const IconHome = ({ size = 18, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" />
  </svg>
);

export const IconBolt = ({ size = 18, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
  </svg>
);

export const IconPackage = ({ size = 18, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="m7.5 4.27 9 5.15" />
    <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
    <path d="m3.3 7 8.7 5 8.7-5" />
    <path d="M12 22V12" />
  </svg>
);

export const IconChart = ({ size = 18, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="M3 3v18h18" />
    <rect x="7" y="12" width="3" height="6" rx="0.5" />
    <rect x="12.5" y="8" width="3" height="10" rx="0.5" />
    <rect x="18" y="5" width="3" height="13" rx="0.5" />
  </svg>
);

export const IconHistory = ({ size = 18, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
    <path d="M3 3v5h5" />
    <path d="M12 7v5l4 2" />
  </svg>
);

export const IconFile = ({ size = 18, color = "currentColor" }) => (
  <svg {...base(size, color)}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
    <path d="M14 2v6h6" />
    <path d="M9 13h6" />
    <path d="M9 17h6" />
  </svg>
);

export const NAV_ICONS = {
  home: IconHome,
  optimize: IconBolt,
  batch: IconPackage,
  result: IconChart,
  history: IconHistory,
  reports: IconFile,
};
