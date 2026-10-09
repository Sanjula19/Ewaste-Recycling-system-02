import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Recycle, FileText, Package, Scale, Zap, Wallet, Leaf, Cloud } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { getManifestSummary } from '../api/client.js';
import LoadingState from '../components/LoadingState.jsx';
import ConnectionBanner from '../components/ConnectionBanner.jsx';
import ErrorState from '../components/ErrorState.jsx';
import MarketOverview from '../components/MarketOverview.jsx';

export default function Dashboard() {
  const { t } = useLanguage();
  const [summary, setSummary] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | ready | offline | error
  const [errorMessage, setErrorMessage] = useState('');

  const load = useCallback(() => {
    setStatus('loading');
    getManifestSummary()
      .then((data) => {
        setSummary(data);
        setStatus('ready');
      })
      .catch((err) => {
        if (err.message === 'NETWORK_UNREACHABLE') {
          setStatus('offline');
        } else {
          setErrorMessage(err.message);
          setStatus('error');
        }
      });
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="page-header">
        <h1>{t('dashboard.title')}</h1>
        <p>{t('dashboard.subtitle')}</p>
      </div>

      <MarketOverview />

      {status === 'loading' && <LoadingState />}
      {status === 'offline' && <ConnectionBanner />}
      {status === 'error' && <ErrorState message={errorMessage} onRetry={load} />}

      {status === 'ready' && summary && (
        <>
          {summary.batch_count === 0 ? (
            <div className="card empty-state">
              <p>{t('dashboard.emptyState')}</p>
            </div>
          ) : (
            <div className="card-grid" style={{ marginBottom: 'var(--space-6)' }}>
              <StatCard icon={Package} label={t('dashboard.batchesProcessed')} value={summary.batch_count} />
              <StatCard icon={Scale} label={t('dashboard.totalTonnage')} value={`${fmt(summary.total_weight_kg)} ${t('common.kg')}`} />
              <StatCard icon={Wallet} label={t('dashboard.totalValue')} value={`Rs. ${fmt(summary.total_value_lkr)}`} />
              <StatCard icon={Leaf} label={t('dashboard.diversionRate')} value={`${summary.landfill_diversion_rate_pct}%`} />
              <StatCard
                icon={Zap}
                label={t('dashboard.totalEnergy')}
                value={`${fmt(summary.total_energy_recovered_kwh)} kWh`}
                sub={summary.total_energy_consumed_kwh > 0
                  ? `${t('manifest.energyConsumed')}: ${fmt(summary.total_energy_consumed_kwh)} kWh`
                  : undefined}
              />
              <StatCard
                icon={Cloud}
                label={t('dashboard.co2Avoided')}
                value={`${fmt(summary.total_co2_avoided_kg)} kg`}
                sub={summary.total_co2_emitted_kg > 0
                  ? `${t('manifest.co2Emitted')}: ${fmt(summary.total_co2_emitted_kg)} kg`
                  : undefined}
              />
            </div>
          )}

          <h2>{t('dashboard.quickActions')}</h2>
          <div className="card-grid">
            <QuickAction to="/forecast" icon={TrendingUp} label={t('dashboard.goForecast')} />
            <QuickAction to="/disposition" icon={Recycle} label={t('dashboard.goDisposition')} />
            <QuickAction to="/manifest" icon={FileText} label={t('dashboard.goManifest')} />
          </div>
        </>
      )}
    </div>
  );
}

/* The backend sends full float precision so cycle totals are exact;
   rounding happens here, once, at the point of display. */
function fmt(n) {
  return Number(n ?? 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <div className="card stat">
      <Icon size={18} color="var(--color-primary)" />
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

function QuickAction({ to, icon: Icon, label }) {
  return (
    <Link to={to} className="card" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', textDecoration: 'none' }}>
      <div className="facility-icon"><Icon size={20} /></div>
      <span style={{ fontWeight: 700, color: 'var(--color-text)' }}>{label}</span>
    </Link>
  );
}
