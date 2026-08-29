import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, Minus, Radio, Clock } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { useNotifications } from '../context/NotificationContext.jsx';
import { getMarketOverview } from '../api/client.js';
import { materialColorVar, materialLabel } from '../utils/materials.js';
import Badge from './Badge.jsx';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';

const POLL_MS = 60_000;

export default function MarketOverview() {
  const { t, intlTag } = useLanguage();
  const { notify } = useNotifications();
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const sellingRef = useRef(null); // metals already known SELL NOW, so we alert only on transition

  useEffect(() => {
    let cancelled = false;

    function load() {
      getMarketOverview()
        .then((resp) => {
          if (cancelled) return;
          setData(resp);
          setStatus('ready');

          const nowSelling = new Set(
            resp.items.filter((i) => i.recommendation === 'SELL NOW').map((i) => i.metal)
          );
          // The banner above already surfaces whatever's SELL NOW on first paint --
          // only pop a toast for a metal that *newly* flips to SELL NOW during this
          // session, so loading the dashboard doesn't fire a wall of toasts at once.
          if (sellingRef.current !== null) {
            for (const item of resp.items) {
              if (item.recommendation === 'SELL NOW' && !sellingRef.current.has(item.metal)) {
                notify({
                  tone: 'alert',
                  title: t('notifications.sellNowTitle'),
                  message: t('notifications.sellNowMessage').replace('{metal}', materialLabel(item.metal, t)),
                });
              }
            }
          }
          sellingRef.current = nowSelling;
        })
        .catch((err) => {
          if (cancelled) return;
          if (err.message === 'NETWORK_UNREACHABLE') setStatus('offline');
          else { setErrorMessage(err.message); setStatus('error'); }
        });
    }

    load();
    const id = setInterval(load, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === 'loading') return <LoadingState />;
  if (status === 'offline') return null; // Dashboard's own ConnectionBanner already covers this
  if (status === 'error') return <ErrorState message={errorMessage} />;
  if (!data) return null;

  const sellingNow = data.items.filter((i) => i.recommendation === 'SELL NOW');

  return (
    <div style={{ marginBottom: 'var(--space-6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
        <h2 style={{ margin: 0 }}>{t('dashboard.marketOverview')}</h2>
        <Badge variant="success" icon={Radio}>{t('dashboard.live')}</Badge>
      </div>

      {sellingNow.length > 0 && (
        <div className="alert alert-danger" role="alert" style={{ marginBottom: 'var(--space-4)' }}>
          <ArrowUpRight size={20} />
          <p>
            <strong>{t('notifications.sellNowTitle')}</strong>{' '}
            {t('notifications.sellNowBanner').replace(
              '{metals}',
              sellingNow.map((i) => materialLabel(i.metal, t)).join(', ')
            )}
          </p>
        </div>
      )}

      <div className="market-grid">
        {data.items.map((item) => (
          <MarketCard key={item.metal} item={item} t={t} intlTag={intlTag} />
        ))}
      </div>
    </div>
  );
}

function MarketCard({ item, t, intlTag }) {
  const isSell = item.recommendation === 'SELL NOW';
  const isUp = item.day_change_pct > 0;
  const isDown = item.day_change_pct < 0;
  const ChangeIcon = isUp ? ArrowUpRight : isDown ? ArrowDownRight : Minus;
  const asOfDate = new Date(item.data_as_of).toLocaleDateString(intlTag, { day: '2-digit', month: 'short', year: 'numeric' });

  return (
    <div className="market-card" style={{ '--chip-color': materialColorVar(item.metal) }}>
      <div className="market-card-top">
        <span className="market-card-name">{materialLabel(item.metal, t)}</span>
        <Badge variant={isSell ? 'success' : 'warning'}>
          {isSell ? t('forecast.sellNow') : t('forecast.hold')}
        </Badge>
      </div>

      <div className="price-pair" style={{ marginTop: 6 }}>
        <span className="price-primary">Rs. {item.current_price_lkr.toLocaleString()}</span>
        <span className="price-secondary">(${item.current_price.toFixed(2)})</span>
      </div>
      <div className="stat-sub">{t('common.kg')}</div>

      <div className={`market-card-change ${isUp ? 'is-up' : isDown ? 'is-down' : ''}`}>
        <ChangeIcon size={15} />
        {Math.abs(item.day_change_pct).toFixed(2)}%
      </div>

      <div className="market-card-footer">
        {item.price_source === 'live' ? (
          <Badge variant="info" icon={Radio}>{t('dashboard.live')}</Badge>
        ) : (
          <span className="market-card-asof"><Clock size={12} /> {t('dashboard.dataAsOf')} {asOfDate}</span>
        )}
      </div>
    </div>
  );
}
