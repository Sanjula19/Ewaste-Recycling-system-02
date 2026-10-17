import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowDownRight, Minus, Radio, Clock, Info } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext.jsx';
import { useNotifications } from '../context/NotificationContext.jsx';
import { getMarketOverview } from '../api/client.js';
import { materialColorVar, materialLabel } from '../utils/materials.js';
import Badge from './Badge.jsx';
import LoadingState from './LoadingState.jsx';
import ErrorState from './ErrorState.jsx';

const POLL_MS = 60_000;
// A price older than this is not "live", whatever the transport says.
const LIVE_MAX_AGE_DAYS = 3;

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

  const holding = data.items.filter((i) => i.recommendation === 'HOLD');

  return (
    <div style={{ marginBottom: 'var(--space-6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
        <h2 style={{ margin: 0 }}>{t('dashboard.marketOverview')}</h2>
        <Badge variant="success" icon={Radio}>{t('dashboard.live')}</Badge>
      </div>

      {/* Neutral, not red. "Sell now" across the board is the ordinary
          outcome of the decision rule when no metal clears its own forecast
          error -- it is not an alert, and styling it as one trained the eye
          to ignore it. When something IS worth holding, that is the news. */}
      {data.items.length > 0 && (
        <div className="alert alert-neutral" role="status" style={{ marginBottom: 'var(--space-4)' }}>
          <Info size={20} />
          <p>
            {holding.length > 0 ? (
              <>
                <strong>{t('dashboard.bannerHoldTitle')}</strong>{' '}
                {t('dashboard.bannerHold').replace(
                  '{metals}',
                  holding.map((i) => materialLabel(i.metal, t)).join(', ')
                )}
              </>
            ) : (
              <>
                <strong>{t('dashboard.bannerSellTitle')}</strong>{' '}
                {t('dashboard.bannerSellAll')}
              </>
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
  const asOfDate = new Date(item.last_price_date || item.data_as_of).toLocaleDateString(
    intlTag, { day: '2-digit', month: 'short', year: 'numeric' });
  // "Live" is only honest for a price from the last few days. An older
  // backend sends no data_age_days, so fall back to the price_source flag
  // it does send rather than claiming staleness it never reported.
  const isFresh = item.data_age_days == null
    ? item.price_source === 'live'
    : item.data_age_days <= LIVE_MAX_AGE_DAYS;

  return (
    <Link
      to={`/forecast?metal=${encodeURIComponent(item.metal)}`}
      className="market-card"
      style={{ '--chip-color': materialColorVar(item.metal) }}
      aria-label={`${materialLabel(item.metal, t)} — ${t('dashboard.valueThisMetal')}`}
    >
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

      {/* One fixed-height row so the freshness indicator sits at the same
          height on every card, whatever its label width. */}
      <div className="market-card-footer">
        <div className="market-card-footer-row">
          {isFresh ? (
            <Badge variant="info" icon={Radio}>{t('dashboard.live')}</Badge>
          ) : (
            <span className="market-card-asof">
              <Clock size={12} /> {t('dashboard.dataUpTo')} {asOfDate}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
