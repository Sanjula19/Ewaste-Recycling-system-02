import React, { useEffect, useState, useCallback } from 'react';
import { Download, RotateCcw, Package, Scale, Zap, Wallet, Leaf, Cloud, History } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { getManifestSummary, getManifestCycles, resetManifestCycle, downloadManifestPdf } from '../api/client.js';
import { materialLabel } from '../utils/materials.js';
import LoadingState from '../components/LoadingState.jsx';
import ConnectionBanner from '../components/ConnectionBanner.jsx';
import ErrorState from '../components/ErrorState.jsx';
import Badge from '../components/Badge.jsx';

export default function Manifest() {
  const { t, intlTag } = useLanguage();
  const [summary, setSummary] = useState(null);
  const [cycles, setCycles] = useState([]);
  const [viewingCycleId, setViewingCycleId] = useState(null); // null = current cycle
  const [status, setStatus] = useState('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const [confirmingReset, setConfirmingReset] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const load = useCallback((cycleId = null) => {
    setStatus('loading');
    Promise.all([getManifestSummary(cycleId), getManifestCycles()])
      .then(([summaryData, cyclesData]) => {
        setSummary(summaryData);
        setCycles(cyclesData.cycles);
        setViewingCycleId(cycleId);
        setStatus('ready');
      })
      .catch((err) => {
        if (err.message === 'NETWORK_UNREACHABLE') setStatus('offline');
        else { setErrorMessage(err.message); setStatus('error'); }
      });
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDownload(cycleId) {
    setDownloading(true);
    try {
      await downloadManifestPdf({ cycleId });
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setDownloading(false);
    }
  }

  async function handleReset() {
    setConfirmingReset(false);
    await resetManifestCycle();
    load();
  }

  if (status === 'loading') return <LoadingState />;
  if (status === 'offline') return <ConnectionBanner />;
  if (status === 'error') return <ErrorState message={errorMessage} onRetry={() => load()} />;
  if (!summary) return null;

  const isViewingPast = viewingCycleId != null;

  return (
    <div>
      <div className="page-header">
        <h1>{t('manifest.title')}</h1>
        <p>{t('manifest.subtitle')}</p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <h2 style={{ margin: 0 }}>
          {isViewingPast ? `${t('manifest.cycleNumber')} #${summary.cycle_id}` : t('manifest.currentCycle')}
          {isViewingPast && <Badge variant="info" icon={History}>{t('manifest.statusClosed')}</Badge>}
        </h2>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {isViewingPast && (
            <button className="btn btn-secondary" onClick={() => load()}>{t('manifest.currentCycle')}</button>
          )}
          <button className="btn btn-secondary" disabled={downloading} onClick={() => handleDownload(viewingCycleId)}>
            <Download size={16} />
            {isViewingPast ? t('manifest.downloadCyclePdf') : t('manifest.downloadCurrentPdf')}
          </button>
          {!isViewingPast && (
            <button className="btn btn-danger" onClick={() => setConfirmingReset(true)}>
              <RotateCcw size={16} />
              {t('manifest.closeCycle')}
            </button>
          )}
        </div>
      </div>

      <div className="card-grid" style={{ marginBottom: 'var(--space-6)' }}>
        <StatCard icon={Package} label={t('dashboard.batchesProcessed')} value={summary.batch_count} />
        <StatCard icon={Scale} label={t('dashboard.totalTonnage')} value={`${summary.total_weight_kg} ${t('common.kg')}`} />
        <StatCard icon={Zap} label={t('dashboard.totalEnergy')} value={`${summary.total_energy_recovered_kwh} kWh`} />
        <StatCard icon={Wallet} label={t('dashboard.totalValue')} value={`Rs. ${summary.total_value_lkr.toLocaleString()}`} />
        <StatCard icon={Leaf} label={t('dashboard.diversionRate')} value={`${summary.landfill_diversion_rate_pct}%`} />
        <StatCard icon={Cloud} label={t('dashboard.co2Avoided')} value={`${summary.total_co2_avoided_kg} kg`} />
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <h3>{t('manifest.batchDetail')}</h3>
        {summary.entries.length === 0 ? (
          <p>{t('manifest.noEntries')}</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('common.manifestRef')}</th>
                  <th>{t('common.material')}</th>
                  <th>{t('manifest.weightKg')}</th>
                  <th>{t('common.route')}</th>
                  <th>{t('manifest.energyKwh')}</th>
                  <th>{t('manifest.valueLkr')}</th>
                </tr>
              </thead>
              <tbody>
                {summary.entries.map((e) => (
                  <tr key={e.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>{e.manifest_id}</td>
                    <td>{materialLabel(e.material, t)}</td>
                    <td>{e.weight_kg}</td>
                    <td>{e.route_or_recommendation}</td>
                    <td>{e.energy_kwh}</td>
                    <td>{e.value_lkr.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <h2>{t('manifest.cycleHistory')}</h2>
      {cycles.map((c) => (
        <div className="cycle-row" key={c.cycle_id}>
          <div>
            <strong>{t('manifest.cycleNumber')} #{c.cycle_id}</strong>{' '}
            <Badge variant={c.status.startsWith('open') ? 'success' : 'info'}>
              {c.status.startsWith('open') ? t('manifest.statusOpen') : t('manifest.statusClosed')}
            </Badge>
            <div className="stat-sub" style={{ marginTop: 4 }}>
              {c.batch_count} batches · {c.total_weight_kg} {t('common.kg')} · Rs. {c.total_value_lkr.toLocaleString()}
            </div>
            <div className="stat-sub">
              {t('manifest.startedAt')}: {new Date(c.started_at).toLocaleString(intlTag)}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <button className="btn btn-secondary" onClick={() => load(c.cycle_id)}>{t('common.status')}</button>
            <button className="btn btn-secondary" onClick={() => handleDownload(c.cycle_id)} disabled={downloading}>
              <Download size={16} /> {t('manifest.downloadCyclePdf')}
            </button>
          </div>
        </div>
      ))}

      {confirmingReset && (
        <ConfirmDialog
          message={t('manifest.closeCycleConfirm')}
          onConfirm={handleReset}
          onCancel={() => setConfirmingReset(false)}
        />
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="card stat">
      <Icon size={18} color="var(--color-primary)" />
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function ConfirmDialog({ message, onConfirm, onCancel }) {
  const { t } = useLanguage();
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 'var(--space-4)',
      }}
    >
      <div className="card" style={{ maxWidth: 420 }}>
        <p style={{ color: 'var(--color-text)' }}>{message}</p>
        <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onCancel}>{t('common.cancel')}</button>
          <button className="btn btn-primary" onClick={onConfirm}>{t('common.confirm')}</button>
        </div>
      </div>
    </div>
  );
}
