import React, { useMemo, useState } from 'react';
import { Flame, Snowflake, MapPin, ChevronDown } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { getDisposition } from '../api/client.js';
import { RESIDUALS } from '../utils/materials.js';
import { SRI_LANKA_LOCATIONS, groupByProvince, findLocation } from '../utils/sriLankaLocations.js';
import LoadingState from '../components/LoadingState.jsx';
import ConnectionBanner from '../components/ConnectionBanner.jsx';
import ErrorState from '../components/ErrorState.jsx';
import MaterialChip from '../components/MaterialChip.jsx';
import SriLankaMap from '../components/SriLankaMap.jsx';

export default function Disposition() {
  const { t } = useLanguage();
  const [wasteType, setWasteType] = useState(RESIDUALS[0].key);
  const [weight, setWeight] = useState('');
  const [facilityName, setFacilityName] = useState('');
  const [locationName, setLocationName] = useState(SRI_LANKA_LOCATIONS[0].name);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [useManualCoords, setUseManualCoords] = useState(false);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [status, setStatus] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState(null);
  const [submittedLocation, setSubmittedLocation] = useState(null);

  const provinceGroups = useMemo(() => groupByProvince(), []);

  function handleSubmit(e) {
    e.preventDefault();
    const w = parseFloat(weight);
    if (!w || w <= 0) return;

    const selectedTown = findLocation(locationName);
    const lat = useManualCoords ? latitude : selectedTown?.lat ?? '';
    const lon = useManualCoords ? longitude : selectedTown?.lon ?? '';
    const locationForMap = useManualCoords
      ? (lat !== '' && lon !== '' ? { name: t('disposition.enteredCoordinates'), lat: Number(lat), lon: Number(lon) } : null)
      : selectedTown;

    setStatus('loading');
    getDisposition({ wasteType, weightKg: w, facilityName, latitude: lat, longitude: lon })
      .then((data) => {
        setResult(data);
        setSubmittedLocation(locationForMap);
        setStatus('ready');
      })
      .catch((err) => {
        if (err.message === 'NETWORK_UNREACHABLE') setStatus('offline');
        else { setErrorMessage(err.message); setStatus('error'); }
      });
  }

  const isHeatSink = result?.thermal_classification === 'inert_heat_sink';

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
              <label htmlFor="location-select">{t('disposition.locationLabel')}</label>
              <select id="location-select" value={locationName} onChange={(e) => setLocationName(e.target.value)}>
                {[...provinceGroups.entries()].map(([province, towns]) => (
                  <optgroup key={province} label={province}>
                    {towns.map((town) => (
                      <option key={town.name} value={town.name}>{town.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <span className="field-hint">{t('disposition.locationHint')}</span>
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
          <div className={`result-hero ${isHeatSink ? 'tone-warning' : 'tone-success'}`}>
            <div>
              <div className="result-hero-label">
                {isHeatSink ? t('disposition.heatSink') : t('disposition.combustible')}
              </div>
              <div className="result-hero-value" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {isHeatSink ? <Snowflake size={26} /> : <Flame size={26} />}
                {result.energy_recovery_kwh.toFixed(2)} kWh
              </div>
            </div>
            <MaterialChip materialKey={wasteType} />
          </div>

          {isHeatSink && (
            <div className="alert alert-info">
              <Snowflake size={20} />
              <p>{t('disposition.heatSinkNote')}</p>
            </div>
          )}

          <div className="card-grid">
            <div className="card">
              <div className="stat-label">{t('disposition.grossEnergy')}</div>
              <div className="stat-value" style={{ fontSize: '1.3rem' }}>{result.gross_energy_kwh?.toFixed(2)} kWh</div>
            </div>
            <div className="card">
              <div className="stat-label">{t('disposition.wastedEnergy')}</div>
              <div className="stat-value" style={{ fontSize: '1.3rem' }}>{result.wasted_energy_kwh?.toFixed(2)} kWh</div>
            </div>
            <div className="card">
              <div className="stat-label">{t('common.route')}</div>
              <div className="stat-value" style={{ fontSize: '1.05rem' }}>{result.disposition_route}</div>
            </div>
          </div>

          <div className="card">
            <h3>{t('disposition.breakdown')}</h3>
            <div className="breakdown-list">
              <div className="breakdown-item">
                <div className="label">{t('disposition.bioOil')}</div>
                <div className="value">{result.energy_breakdown.bio_oil_liters} L</div>
              </div>
              <div className="breakdown-item">
                <div className="label">{t('disposition.syngas')}</div>
                <div className="value">{result.energy_breakdown.syngas_kwh} kWh</div>
              </div>
              <div className="breakdown-item">
                <div className="label">{t('disposition.char')}</div>
                <div className="value">{result.energy_breakdown.char_kg} {t('common.kg')}</div>
              </div>
            </div>
          </div>

          {result.nearest_treatment_facility && (
            <div className="card facility-card">
              <div className="facility-icon"><MapPin size={20} /></div>
              <div style={{ flex: 1 }}>
                <h3 style={{ marginBottom: 4 }}>{t('disposition.nearestFacility')}</h3>
                <p style={{ marginBottom: 4, color: 'var(--color-text)', fontWeight: 600 }}>
                  {result.nearest_treatment_facility.name}
                </p>
                <p style={{ margin: 0 }}>
                  {t('disposition.distance')}: {result.nearest_treatment_facility.distance_km} km
                  {result.nearest_treatment_facility.feed_in_tariff_lkr_per_kwh && (
                    <> · {t('disposition.tariff')}: Rs. {result.nearest_treatment_facility.feed_in_tariff_lkr_per_kwh}/kWh</>
                  )}
                </p>
              </div>
            </div>
          )}

          {result.nearest_treatment_facility && submittedLocation && (
            <div className="card">
              <h3>{t('disposition.mapTitle')}</h3>
              <SriLankaMap location={submittedLocation} facility={result.nearest_treatment_facility} />
            </div>
          )}

          <div className="card-grid">
            <div className="card">
              <div className="stat-label">{t('disposition.revenue')}</div>
              <div className="price-pair" style={{ marginTop: 6 }}>
                <span className="price-primary">Rs. {result.estimated_revenue_lkr?.toLocaleString()}</span>
                <span className="price-secondary">(${result.estimated_revenue_usd?.toFixed(2)})</span>
              </div>
            </div>
            <div className="card">
              <div className="stat-label">{t('disposition.co2Avoided')}</div>
              <div className="stat-value" style={{ fontSize: '1.3rem' }}>{result.co2_avoided_kg} kg</div>
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
