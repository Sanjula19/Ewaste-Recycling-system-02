import React, { useEffect, useMemo, useState } from 'react';
import { Flame, MapPin, ChevronDown, Recycle, Truck, AlertTriangle, ExternalLink, Zap } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { getDisposition, getLocalAuthorities } from '../api/client.js';
import { RESIDUALS } from '../utils/materials.js';
import LoadingState from '../components/LoadingState.jsx';
import ConnectionBanner from '../components/ConnectionBanner.jsx';
import ErrorState from '../components/ErrorState.jsx';
import MaterialChip from '../components/MaterialChip.jsx';
import SriLankaMap from '../components/SriLankaMap.jsx';

const TECH_KEY = {
  pyrolysis: 'disposition.techPyrolysis',
  incineration_wte: 'disposition.techIncinerationWte',
  mechanical_recycling: 'disposition.techMechanicalRecycling',
};

/*
  One facility card, used for both the recommendation and the alternative.

  Everything a council needs to challenge the routing is on the card: the
  operator, the town, the straight-line distance, the technology, whether
  the entry is verified, and a link to the source it came from. A facility
  with no source says so rather than leaving the absence to be noticed.
*/
function FacilityCard({ facility, tone, heading, t }) {
  if (!facility) return null;
  return (
    <div className="card facility-card">
      <div className="facility-icon"><MapPin size={20} /></div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          <h3 style={{ margin: 0 }}>{heading}</h3>
          <span className={`badge badge-${tone}`}>{t(TECH_KEY[facility.technology] ?? facility.technology)}</span>
          {facility.unconfirmed && (
            <span className="badge badge-warning" title={t('disposition.unconfirmedTitle')}>
              {t('disposition.unconfirmed')}
            </span>
          )}
        </div>

        <p style={{ marginBottom: 4, color: 'var(--color-text)', fontWeight: 600 }}>
          {facility.name} ({facility.operator}), {facility.town}
          {typeof facility.distance_km === 'number' && ` — ${facility.distance_km} km`}
        </p>

        <p style={{ margin: 0, fontSize: '0.85rem' }}>
          {facility.exports_electricity && facility.tariff_lkr_per_kwh != null && (
            <>{t('disposition.tariff')}: Rs. {facility.tariff_lkr_per_kwh}/kWh · </>
          )}
          {facility.source_url ? (
            <a href={facility.source_url} target="_blank" rel="noreferrer noopener"
               style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {t('disposition.viewSource')} <ExternalLink size={12} />
            </a>
          ) : (
            <span style={{ color: 'var(--color-text-muted)' }}>{t('disposition.noSource')}</span>
          )}
        </p>
      </div>
    </div>
  );
}

export default function Disposition() {
  const { t } = useLanguage();
  const [wasteType, setWasteType] = useState(RESIDUALS[0].key);
  const [weight, setWeight] = useState('');
  const [facilityName, setFacilityName] = useState('');
  const [authorities, setAuthorities] = useState([]);
  const [localAuthority, setLocalAuthority] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [useManualCoords, setUseManualCoords] = useState(false);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [status, setStatus] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState(null);

  // The selector is fed from the backend register, not a second copy of the
  // same coordinates in the frontend -- the two used to drift.
  useEffect(() => {
    let cancelled = false;
    getLocalAuthorities()
      .then((data) => {
        if (cancelled) return;
        setAuthorities(data.local_authorities ?? []);
        setLocalAuthority((cur) => cur || data.default || data.local_authorities?.[0]?.name || '');
      })
      .catch(() => { /* routing still works: the server falls back to its default */ });
    return () => { cancelled = true; };
  }, []);

  const provinceGroups = useMemo(() => {
    const groups = new Map();
    for (const la of authorities) {
      const key = la.province || la.district || '—';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(la);
    }
    return groups;
  }, [authorities]);

  function handleSubmit(e) {
    e.preventDefault();
    const w = parseFloat(weight);
    if (!w || w <= 0) return;

    setStatus('loading');
    getDisposition({
      wasteType,
      weightKg: w,
      facilityName,
      localAuthority: useManualCoords ? undefined : localAuthority,
      latitude: useManualCoords ? latitude : undefined,
      longitude: useManualCoords ? longitude : undefined,
    })
      .then((data) => { setResult(data); setStatus('ready'); })
      .catch((err) => {
        if (err.message === 'NETWORK_UNREACHABLE') setStatus('offline');
        else {
          // Glass is no longer selectable here, so this only fires for a
          // direct API call -- but translate it rather than surfacing the
          // server's English string to a Sinhala or Tamil operator.
          setErrorMessage(
            /glass/i.test(err.message) ? t('disposition.glassRejected') : err.message
          );
          setStatus('error');
        }
      });
  }

  const isMechanical = result?.disposition_method === 'mechanical';
  const originForMap = result?.origin
    ? { name: result.origin.name, lat: result.origin.latitude, lon: result.origin.longitude }
    : null;
  const hasPlottableFacility =
    (result?.recommended_facility?.latitude != null) ||
    (result?.alternative_facility?.latitude != null);

  return (
    <div>
      <div className="page-header">
        <h1>{t('disposition.title')}</h1>
        <p>{t('disposition.subtitle')}</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="material-select">{t('disposition.selectMaterial')}</label>
              <select id="material-select" value={wasteType} onChange={(e) => setWasteType(e.target.value)}>
                {RESIDUALS.map((m) => (
                  <option key={m.key} value={m.key}>{t(m.i18nKey)}</option>
                ))}
              </select>
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="weight-input-d">{t('common.weightKg')}</label>
              <input
                id="weight-input-d"
                type="number"
                min="0.01"
                step="0.01"
                placeholder={t('forecast.weightPlaceholder')}
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={status === 'loading'}>
              {t('disposition.submit')}
            </button>
          </div>

          <div className="field">
            <label htmlFor="facility-name">{t('disposition.facilityNameLabel')}</label>
            <input
              id="facility-name"
              type="text"
              placeholder={t('disposition.facilityNamePlaceholder')}
              value={facilityName}
              onChange={(e) => setFacilityName(e.target.value)}
            />
          </div>

          {!useManualCoords && (
            <div className="field">
              <label htmlFor="authority-select">{t('disposition.localAuthorityLabel')}</label>
              <select
                id="authority-select"
                value={localAuthority}
                onChange={(e) => setLocalAuthority(e.target.value)}
                disabled={authorities.length === 0}
              >
                {[...provinceGroups.entries()].map(([province, list]) => (
                  <optgroup key={province} label={province}>
                    {list.map((la) => (
                      <option key={la.name} value={la.name}>
                        {la.name} ({la.district})
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <span className="field-hint">{t('disposition.localAuthorityHint')}</span>
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--color-primary)', fontWeight: 600, fontSize: '0.85rem', padding: 0, marginBottom: showAdvanced ? 'var(--space-3)' : 0 }}
          >
            <ChevronDown size={16} style={{ transform: showAdvanced ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }} />
            {t('disposition.advanced')}
          </button>

          {showAdvanced && (
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>
                <input type="checkbox" checked={useManualCoords} onChange={(e) => setUseManualCoords(e.target.checked)} />
                {t('disposition.useManualCoords')}
              </label>
            </div>
          )}

          {showAdvanced && useManualCoords && (
            <div className="form-row" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <div className="field" style={{ marginBottom: 0 }}>
                <label htmlFor="lat">{t('disposition.latitude')}</label>
                <input id="lat" type="number" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} placeholder="6.9271" />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label htmlFor="lon">{t('disposition.longitude')}</label>
                <input id="lon" type="number" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} placeholder="79.8612" />
              </div>
            </div>
          )}
        </form>
      </div>

      {status === 'loading' && <LoadingState />}
      {status === 'offline' && <div style={{ marginTop: 'var(--space-4)' }}><ConnectionBanner /></div>}
      {status === 'error' && <div style={{ marginTop: 'var(--space-4)' }}><ErrorState message={errorMessage} /></div>}

      {status === 'ready' && result && (
        <div className="result-section">
          {/* Mechanical recycling has no thermal figures at all -- the hero
              carries the process itself rather than a meaningless 0 kWh. */}
          {isMechanical ? (
            <div className="result-hero tone-info">
              <div>
                <div className="result-hero-label">{t('disposition.methodMechanical')}</div>
                <div className="result-hero-value" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Recycle size={26} />
                  {t('disposition.mechanicalHeadline')}
                </div>
              </div>
              <MaterialChip materialKey={wasteType} />
            </div>
          ) : (
            <div className="result-hero tone-success">
              <div>
                <div className="result-hero-label">{t('disposition.energyContent')}</div>
                <div className="result-hero-value" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Flame size={26} />
                  {result.energy_recovery_kwh.toFixed(2)} kWh
                </div>
              </div>
              <MaterialChip materialKey={wasteType} />
            </div>
          )}

          {/* Why there is no recommendation, when there is none. Stated
              before the alternative, so nobody reads the fallback as the
              system's actual advice. */}
          {result.recommendation_blocked_reason && (
            <div className="alert alert-warning">
              <AlertTriangle size={20} />
              <div>
                <p style={{ fontWeight: 700 }}>{t('disposition.noRecommendation')}</p>
                <p>{result.recommendation_blocked_reason}</p>
              </div>
            </div>
          )}

          {result.dispatch_note && (
            <div className="alert alert-info">
              <Truck size={20} />
              <div>
                <p style={{ fontWeight: 700 }}>{t('disposition.dispatchNote')}</p>
                <p>{result.dispatch_note}</p>
              </div>
            </div>
          )}

          <FacilityCard
            facility={result.recommended_facility}
            tone="success"
            heading={t('disposition.recommended')}
            t={t}
          />
          <FacilityCard
            facility={result.alternative_facility}
            tone="info"
            heading={t('disposition.alternative')}
            t={t}
          />

          {/* Facilities the register holds but routing could not use. Shown
              so a missing plant is visible rather than silently absent. */}
          {result.facilities_excluded?.length > 0 && (
            <div className="card">
              <h3>{t('disposition.excludedTitle')}</h3>
              <div className="breakdown-list">
                {result.facilities_excluded.map((x) => (
                  <div className="breakdown-item" key={x.id} style={{ alignItems: 'flex-start' }}>
                    <div className="label">
                      {x.name} ({x.operator}), {x.town}
                    </div>
                    <div className="value" style={{ fontWeight: 400, fontSize: '0.82rem', textAlign: 'right', maxWidth: '60%' }}>
                      {x.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!isMechanical && (
            <>
              <div className="card-grid">
                <div className="card">
                  <div className="stat-label">{t('common.route')}</div>
                  <div className="stat-value" style={{ fontSize: '1.05rem' }}>{result.disposition_route}</div>
                </div>
                <div className="card">
                  <div className="stat-label">{t('disposition.co2Avoided')}</div>
                  <div className="stat-value" style={{ fontSize: '1.3rem' }}>
                    {result.co2_avoided_kg.toFixed(2)} kg
                  </div>
                </div>
                <div className="card">
                  <div className="stat-label">{t('common.weightKg')}</div>
                  <div className="stat-value" style={{ fontSize: '1.3rem' }}>{result.weight_kg} {t('common.kg')}</div>
                </div>
              </div>

              {/* Electricity: a value, or the reason there isn't one. Never a
                  blank that could be read as zero. */}
              {result.electricity && (
                <div className="card">
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Zap size={18} /> {t('disposition.electricityTitle')}
                  </h3>
                  {result.electricity.reported ? (
                    <>
                      <div className="result-hero-value" style={{ fontSize: '1.4rem' }}>
                        Rs. {result.electricity.value_lkr?.toLocaleString()}
                      </div>
                      <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                        {result.electricity.label}
                        {result.electricity.facility_name && ` — ${result.electricity.facility_name}`}
                        {result.electricity.tariff_lkr_per_kwh != null &&
                          ` · Rs. ${result.electricity.tariff_lkr_per_kwh}/kWh`}
                      </p>
                    </>
                  ) : (
                    <>
                      <div style={{ fontWeight: 700, color: 'var(--color-text-muted)' }}>
                        {t('disposition.electricityNotReported')}
                      </div>
                      <p style={{ fontSize: '0.85rem', marginTop: 4 }}>
                        {result.electricity.not_reported_reason}
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Pyrolysis products: a mass split, and no money figure. */}
              {result.pyrolysis_products && (
                <div className="card">
                  <h3>{t('disposition.productsTitle')}</h3>
                  <div className="breakdown-list">
                    <div className="breakdown-item">
                      <div className="label">{t('disposition.bioOil')} ({result.pyrolysis_products.oil_pct}%)</div>
                      <div className="value">
                        {result.pyrolysis_products.bio_oil_kg} {t('common.kg')} · {result.pyrolysis_products.bio_oil_liters} L
                      </div>
                    </div>
                    <div className="breakdown-item">
                      <div className="label">{t('disposition.syngas')} ({result.pyrolysis_products.gas_pct}%)</div>
                      <div className="value">{result.pyrolysis_products.syngas_kg} {t('common.kg')}</div>
                    </div>
                    <div className="breakdown-item">
                      <div className="label">{t('disposition.char')} ({result.pyrolysis_products.char_pct}%)</div>
                      <div className="value">{result.pyrolysis_products.char_kg} {t('common.kg')}</div>
                    </div>
                    <div className="breakdown-item">
                      <div className="label">{t('disposition.productsValue')}</div>
                      <div className="value" style={{ color: 'var(--color-text-muted)' }}>
                        {t('disposition.valueNotEstimated')}
                      </div>
                    </div>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
                    {result.pyrolysis_products.value_note}
                  </p>
                </div>
              )}
            </>
          )}

          {originForMap && hasPlottableFacility && (
            <div className="card">
              <h3>{t('disposition.mapTitle')}</h3>
              <SriLankaMap
                location={originForMap}
                facility={result.recommended_facility}
                alternative={result.alternative_facility}
              />
            </div>
          )}

          <div className="card-grid">
            <div className="card">
              <div className="stat-label">{t('disposition.origin')}</div>
              <div className="stat-value" style={{ fontSize: '1.05rem' }}>{result.origin?.name}</div>
            </div>
            <div className="card">
              <div className="stat-label">{t('disposition.manifestId')}</div>
              <div className="stat-value" style={{ fontSize: '0.95rem', fontFamily: 'monospace' }}>{result.manifest_id}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
