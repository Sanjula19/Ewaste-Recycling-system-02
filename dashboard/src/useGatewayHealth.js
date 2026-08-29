import { useEffect, useState } from 'react';
import { GATEWAY_URL } from './config.js';

const POLL_INTERVAL_MS = 15000;

// Simple polling hook around the gateway's own /health aggregator.
// Deliberately dumb: one fetch, one interval, no retries/backoff — this is
// a status indicator, not a monitoring system.
export function useGatewayHealth() {
  const [health, setHealth] = useState({
    loading: true,
    gatewayReachable: false,
    services: {},
    overallStatus: 'unknown',
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(`${GATEWAY_URL}/health`);
        if (!res.ok) throw new Error(`Gateway returned HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setHealth({
            loading: false,
            gatewayReachable: true,
            services: data.services || {},
            overallStatus: data.overall_status || 'unknown',
            error: null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setHealth({
            loading: false,
            gatewayReachable: false,
            services: {},
            overallStatus: 'unreachable',
            error: err.message,
          });
        }
      }
    }

    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return health;
}
