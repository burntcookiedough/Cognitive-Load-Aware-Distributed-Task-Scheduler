import { useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { CLS_SERVICE_URL, USER_ID, TELEMETRY_INTERVAL } from '../config';

/**
 * useTelemetry — captures browser interaction signals and batches them
 * to the Cognitive Load Service every TELEMETRY_INTERVAL ms.
 *
 * Captures:
 *   - keystrokes count
 *   - inter-key intervals → avg + variance
 *   - idle duration (no key/mouse activity)
 *   - tab visibility changes (tab_switches)
 *   - window focus/blur (focus_changes)
 *   - context switches (derived from visibility + focus combined)
 */
export function useTelemetry(enabled = true, onUpdate = null) {
  const win = useRef({
    keystrokes:       0,
    intervals:        [],
    lastKeyTime:      null,
    idleStart:        Date.now(),
    tabSwitches:      0,
    focusChanges:     0,
    contextSwitches:  0,
    isIdle:           false,
  });

  const timerRef   = useRef(null);
  const idleTimer  = useRef(null);
  const IDLE_THRESHOLD = 5000; // 5s of inactivity = idle

  const markActive = useCallback(() => {
    const w = win.current;
    if (w.isIdle) {
      w.isIdle    = false;
      w.idleStart = null;
    }
    // Reset idle timer
    clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => {
      win.current.isIdle    = true;
      win.current.idleStart = Date.now();
    }, IDLE_THRESHOLD);
  }, []);

  const flush = useCallback(async () => {
    const w = win.current;

    // Compute inter-key stats
    const ivs = w.intervals;
    const avg  = ivs.length > 0 ? ivs.reduce((a, b) => a + b, 0) / ivs.length : 0;
    const variance = ivs.length > 1
      ? ivs.reduce((sum, x) => sum + (x - avg) ** 2, 0) / ivs.length
      : 0;

    // Idle time in seconds
    const idleMs = w.isIdle && w.idleStart != null
      ? Date.now() - w.idleStart
      : 0;

    const payload = {
      user_id:                USER_ID,
      timestamp:              new Date().toISOString(),
      keystrokes:             w.keystrokes,
      avg_inter_key_interval: Math.round(avg),
      typing_variance:        Math.round(variance),
      idle_duration:          parseFloat((idleMs / 1000).toFixed(2)),
      tab_switches:           w.tabSwitches,
      focus_changes:          w.focusChanges,
      context_switches:       w.contextSwitches,
    };

    // Reset window accumulators (keep idle state)
    win.current = {
      ...win.current,
      keystrokes:      0,
      intervals:       [],
      lastKeyTime:     null,
      tabSwitches:     0,
      focusChanges:    0,
      contextSwitches: 0,
    };

    if (onUpdate) onUpdate(payload);

    try {
      await axios.post(`${CLS_SERVICE_URL}/telemetry`, payload);
    } catch {
      // Silent fail — telemetry is non-critical
    }
  }, [onUpdate]);

  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (e) => {
      const now = Date.now();
      const w   = win.current;
      w.keystrokes++;
      if (w.lastKeyTime !== null) {
        const interval = now - w.lastKeyTime;
        if (interval < 2000) {               // ignore gaps > 2s (not typing)
          w.intervals.push(interval);
          if (w.intervals.length > 120) w.intervals.shift();
        }
      }
      w.lastKeyTime = now;
      markActive();
    };

    const onMouseMove = () => markActive();

    const onVisibility = () => {
      win.current.tabSwitches++;
      win.current.contextSwitches++;
    };

    const onFocus = () => {
      win.current.focusChanges++;
      markActive();
    };

    const onBlur = () => {
      win.current.focusChanges++;
      win.current.isIdle    = true;
      win.current.idleStart = Date.now();
    };

    document.addEventListener('keydown',      onKeyDown);
    document.addEventListener('mousemove',    onMouseMove, { passive: true });
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', onFocus);
    window.addEventListener('blur',  onBlur);

    // Start idle timer
    idleTimer.current = setTimeout(() => {
      win.current.isIdle    = true;
      win.current.idleStart = Date.now();
    }, IDLE_THRESHOLD);

    timerRef.current = setInterval(flush, TELEMETRY_INTERVAL);

    return () => {
      document.removeEventListener('keydown',      onKeyDown);
      document.removeEventListener('mousemove',    onMouseMove);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('blur',  onBlur);
      clearInterval(timerRef.current);
      clearTimeout(idleTimer.current);
    };
  }, [enabled, flush, markActive]);
}
