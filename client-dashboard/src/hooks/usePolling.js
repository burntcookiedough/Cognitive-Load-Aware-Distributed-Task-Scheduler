import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { POLL_INTERVAL } from '../config';

/**
 * usePolling — polls a URL at a fixed interval and returns { data, loading, error }.
 * Automatically aborts stale requests and cleans up on unmount.
 */
export function usePolling(url, interval = POLL_INTERVAL, enabled = true) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const abortRef = useRef(null);

  useEffect(() => {
    if (!enabled || !url) return;

    let active = true;

    const fetch = async () => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const res = await axios.get(url, { signal: ctrl.signal });
        if (active) {
          setData(res.data);
          setError(null);
          setLoading(false);
        }
      } catch (e) {
        if (active && !axios.isCancel(e)) {
          setError(e.message);
          setLoading(false);
        }
      }
    };

    fetch();
    const id = setInterval(fetch, interval);

    return () => {
      active = false;
      clearInterval(id);
      abortRef.current?.abort();
    };
  }, [url, interval, enabled]);

  return { data, loading, error };
}
