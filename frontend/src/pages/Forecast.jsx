import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Info } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { useNotifications } from '../context/NotificationContext.jsx';
import { getForecast } from '../api/client.js';
import { METALS, materialColorVar, materialLabel } from '../utils/materials.js';
import LoadingState from '../components/LoadingState.jsx';
import ConnectionBanner from '../components/ConnectionBanner.jsx';
import ErrorState from '../components/ErrorState.jsx';
import MaterialChip from '../components/MaterialChip.jsx';

export default function Forecast() {
  const { t, intlTag } = useLanguage();
  const { notify } = useNotifications();
  const [metal, setMetal] = useState(METALS[0].key);
  const [weight, setWeight] = useState('');
  const [status, setStatus] = useState('idle'); // idle | loading | ready | offline | error
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState(null);

  function handleSubmit(e) {
    e.preventDefault();
    const w = parseFloat(weight);
    if (!w || w <= 0) return;

    setStatus('loading');
    getForecast(metal, w)
      .then((data) => {
        setResult(data);
        setStatus('ready');
        if (data.recommendation === 'SELL NOW') {
          notify({
            tone: 'alert',
            title: t('notifications.sellNowTitle'),
            message: t('notifications.sellNowMessage').replace('{metal}', materialLabel(metal, t)),
          });
        }
      })
      .catch((err) => {
        if (err.message === 'NETWORK_UNREACHABLE') setStatus('offline');
        else { setErrorMessage(err.message); setStatus('error'); }
      });
  }

  const isSell = result?.recommendation === 'SELL NOW';
  const chartData = result?.forecast_90d?.map((p) => ({
    date: p.date,
    [t('forecast.currentPrice')]: p.price_lkr,
    lower: p.lower_bound_lkr,
    upper: p.upper_bound_lkr,
  }));

  return (
    <div>
      <div className="page-header">
        <h1>{t('forecast.title')}</h1>
        <p>{t('forecast.subtitle')}</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="metal-select">{t('forecast.selectMetal')}</label>
              <select id="metal-select" value={metal} onChange={(e) => setMetal(e.target.value)}>
                {METALS.map((m) => (
                  <option key={m.key} value={m.key}>{t(m.i18nKey)}</option>
                ))}
              </select>
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="weight-input">{t('common.weightKg')}</label>
              <input
                id="weight-input"
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
              {t('forecast.submit')}
            </button>
          </div>
        </form>
      </div>

      {status === 'loading' && <LoadingState />}
      {status === 'offline' && <div style={{ marginTop: 'var(--space-4)' }}><ConnectionBanner /></div>}
      {status === 'error' && <div style={{ marginTop: 'var(--space-4)' }}><ErrorState message={errorMessage} /></div>}

      {status === 'ready' && result && (
        <div className="result-section">
          <div className={`result-hero ${isSell ? 'tone-success' : 'tone-warning'}`}>
            <div>
              <div className="result-hero-label">{t('forecast.recommendation')}</div>
              <div className="result-hero-value" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {isSell ? <TrendingUp size={26} /> : <TrendingDown size={26} />}
                {isSell ? t('forecast.sellNow') : t('forecast.hold')}
              </div>
            </div>
            <MaterialChip materialKey={metal} />
          </div>

          <div className="action-note">
            <strong>{isSell ? t('forecast.actionSell') : t('forecast.actionHold')}</strong>
          </div>

          <div className="card-grid">
            <div className="card">
              <div className="stat-label">{t('forecast.currentPrice')} ({t('forecast.perKg')})</div>
              <div className="price-pair" style={{ marginTop: 6 }}>
                <span className="price-primary">Rs. {result.current_price_lkr.toLocaleString()}</span>
                <span className="price-secondary">(${result.current_price.toFixed(2)})</span>
              </div>
            </div>
            <div className="card">
              <div className="stat-label">{t('forecast.batchValue')}</div>
              {result.recommendation === 'SELL NOW' ? (
                <div className="price-pair" style={{ marginTop: 6 }}>
                  <span className="price-primary">Rs. {result.profit_if_sell_lkr?.toLocaleString()}</span>
                  <span className="price-secondary">(${result.profit_if_sell?.toFixed(2)})</span>
                </div>
              ) : (
                <div style={{ marginTop: 6 }}>
                  <div className="price-pair">
                    <span className="price-primary">Rs. {result.expected_peak_price_lkr?.toLocaleString()}</span>
                    <span className="price-secondary">(${result.expected_peak_price?.toFixed(2)})</span>
                  </div>
                  <span className="stat-sub">{t('forecast.expectedPeakOn')} {result.expected_peak_date}</span>
                </div>
              )}
            </div>
          </div>

          <div className="card chart-card">
            <h3>{t('forecast.forecastChart')}</h3>
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    interval={Math.floor((chartData?.length || 90) / 6)}
                  />
                  <YAxis tick={{ fontSize: 11 }} width={70} tickFormatter={(v) => `Rs.${Math.round(v)}`} />
                  <Tooltip formatter={(v) => `Rs. ${Number(v).toLocaleString()}`} />
                  <Legend />
                  <Line type="monotone" dataKey="upper" stroke="var(--color-text-faint)" strokeDasharray="4 4" dot={false} name="Upper bound" />
                  <Line type="monotone" dataKey="lower" stroke="var(--color-text-faint)" strokeDasharray="4 4" dot={false} name="Lower bound" />
                  <Line type="monotone" dataKey={t('forecast.currentPrice')} stroke={materialColorVar(metal)} strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card-grid">
            <div className="card">
              <h3>{t('forecast.accuracy')}</h3>
              <div className="breakdown-list">
                <div className="breakdown-item">
                  <div className="label">{t('forecast.mape')}</div>
                  <div className="value">{result.mape}%</div>
                </div>
                <div className="breakdown-item">
                  <div className="label">{t('forecast.rmse')}</div>
                  <div className="value">${result.rmse}</div>
                </div>
                <div className="breakdown-item">
                  <div className="label">{t('forecast.modelUsed')}</div>
                  <div className="value" style={{ fontSize: '0.85rem' }}>{result.model_used}</div>
                </div>
              </div>
            </div>
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Info size={16} /> {t('forecast.exchangeRate')}
              </h3>
              <p style={{ margin: 0 }}>
                1 USD = Rs. {result.fx.usd_lkr.toFixed(2)}
                {' — '}
                {result.fx.source === 'live' && t('forecast.rateSourceLive')}
                {result.fx.source === 'cached' && t('forecast.rateSourceCached')}
                {result.fx.source === 'fallback' && t('forecast.rateSourceFallback')}
                {' '}({t('forecast.rateAsOf')} {result.fx.as_of.slice(0, 10)})
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
