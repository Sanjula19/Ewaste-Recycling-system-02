import React from 'react';
import { MapPin, Factory } from 'lucide-react';

/*
  Self-contained inline SVG map of Sri Lanka -- no tile server, no mapping
  library dependency (none is installed in package.json, and this
  environment's npm/network access isn't reliable enough to add one).
  A simplified coastal outline, linearly projected from real lat/lon, is
  "good enough to show which part of the country this is" -- the same bar
  facility_service.py's Haversine-not-road-routing comment already sets
  for this component, not a survey-grade chart.

  Projection: equirectangular over Sri Lanka's real bounding box
  (lat 5.9-9.9N, lon 79.5-81.9E), both axes scaled 100px/degree so the
  island's real aspect ratio is preserved.
*/

const LAT_MIN = 5.9;
const LAT_MAX = 9.9;
const LON_MIN = 79.5;
const LON_MAX = 81.9;
const SCALE = 100; // px per degree, both axes -- keeps aspect ratio true
export const VIEW_W = (LON_MAX - LON_MIN) * SCALE; // 240
export const VIEW_H = (LAT_MAX - LAT_MIN) * SCALE; // 400

function project(lat, lon) {
  const x = (lon - LON_MIN) * SCALE;
  const y = (LAT_MAX - lat) * SCALE;
  return [x, y];
}

// Simplified coastal outline (clockwise from the northern Jaffna
// peninsula), hand-digitized from well-known landmarks -- not a
// cartographic-survey boundary.
const OUTLINE_LATLON = [
  [9.82, 80.23], [9.70, 80.40], [9.50, 80.55], [9.30, 80.75], [8.90, 81.05],
  [8.59, 81.22], [8.10, 81.35], [7.72, 81.70], [7.40, 81.75], [7.10, 81.75],
  [6.80, 81.75], [6.50, 81.50], [6.30, 81.30], [6.12, 81.12], [5.92, 80.59],
  [6.05, 80.22], [6.48, 79.98], [6.71, 79.90], [6.93, 79.86], [7.21, 79.84],
  [7.58, 79.80], [8.04, 79.83], [8.35, 79.75], [8.70, 79.75], [8.98, 79.90],
  [9.30, 79.95], [9.55, 80.05], [9.66, 80.02], [9.82, 80.23],
];

const OUTLINE_PATH = OUTLINE_LATLON
  .map(([lat, lon], i) => {
    const [x, y] = project(lat, lon);
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
  })
  .join(' ') + ' Z';

export default function SriLankaMap({ location, facility }) {
  const [locX, locY] = location ? project(location.lat, location.lon) : [null, null];
  const [facX, facY] = facility ? project(facility.latitude, facility.longitude) : [null, null];

  return (
    <div className="sl-map-wrap">
      <svg
        className="sl-map-svg"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label="Map of Sri Lanka showing the entered location and nearest treatment facility"
      >
        <path
          d={OUTLINE_PATH}
          fill="var(--color-surface-alt)"
          stroke="var(--color-border-strong)"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />

        {location && facility && (
          <line
            x1={locX} y1={locY} x2={facX} y2={facY}
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />
        )}

        {facility && (
          <g>
            <circle cx={facX} cy={facY} r="6" fill="var(--color-success)" stroke="var(--color-surface)" strokeWidth="1.5" />
            <circle cx={facX} cy={facY} r="10" fill="none" stroke="var(--color-success)" strokeWidth="1" opacity="0.5" />
          </g>
        )}

        {location && (
          <g>
            <circle cx={locX} cy={locY} r="6" fill="var(--color-primary)" stroke="var(--color-surface)" strokeWidth="1.5" />
            <circle cx={locX} cy={locY} r="10" fill="none" stroke="var(--color-primary)" strokeWidth="1" opacity="0.5" />
          </g>
        )}
      </svg>

      <div className="sl-map-legend">
        {location && (
          <div className="sl-map-legend-item">
            <span className="sl-map-dot" style={{ background: 'var(--color-primary)' }} />
            <MapPin size={14} />
            <span>{location.name}</span>
          </div>
        )}
        {facility && (
          <div className="sl-map-legend-item">
            <span className="sl-map-dot" style={{ background: 'var(--color-success)' }} />
            <Factory size={14} />
            <span>{facility.name}</span>
          </div>
        )}
        {facility && typeof facility.distance_km === 'number' && (
          <div className="stat-sub">{facility.distance_km} km</div>
        )}
      </div>
    </div>
  );
}
