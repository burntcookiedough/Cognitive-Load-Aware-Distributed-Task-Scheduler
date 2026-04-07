import { useEffect, useRef } from 'react';
import { CLS_COLORS } from '../config';

/**
 * CLSGauge — animated SVG arc gauge showing the CLS score.
 *
 * The gauge is a 220° arc (from 200° to 340° = bottom-left to bottom-right)
 * filled proportionally by cls_score ∈ [0,1].
 */
export default function CLSGauge({ clsScore = 0, clsState = 'LOW', size = 200 }) {
  const prevRef  = useRef(clsScore);
  const color    = CLS_COLORS[clsState] ?? '#00d4ff';

  const R        = size * 0.38;          // arc radius
  const cx       = size / 2;
  const cy       = size / 2;

  // Arc spans 220 degrees: from 160° to 20° (going clockwise through bottom)
  const START_DEG = 160;
  const SWEEP_DEG = 220;

  const polar = (deg) => {
    const rad = (deg * Math.PI) / 180;
    return { x: cx + R * Math.cos(rad), y: cy + R * Math.sin(rad) };
  };

  const endDeg  = START_DEG + SWEEP_DEG * clsScore;
  const p0      = polar(START_DEG);
  const pEnd    = polar(endDeg);
  const largeArc= SWEEP_DEG * clsScore > 180 ? 1 : 0;

  const fullEnd = polar(START_DEG + SWEEP_DEG);

  // Background track path (full arc)
  const trackPath = [
    `M ${p0.x} ${p0.y}`,
    `A ${R} ${R} 0 1 1 ${fullEnd.x} ${fullEnd.y}`,
  ].join(' ');

  // Filled arc path
  const fillPath = clsScore < 0.01 ? '' : [
    `M ${p0.x} ${p0.y}`,
    `A ${R} ${R} 0 ${largeArc} 1 ${pEnd.x} ${pEnd.y}`,
  ].join(' ');

  const pct = Math.round(clsScore * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg
        width={size} height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ overflow: 'visible', filter: `drop-shadow(0 0 12px ${color}55)` }}
      >
        {/* Glow filter */}
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Background track */}
        <path d={trackPath} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={size * 0.06} strokeLinecap="round" />

        {/* Filled arc */}
        {fillPath && (
          <path
            d={fillPath}
            fill="none"
            stroke={color}
            strokeWidth={size * 0.06}
            strokeLinecap="round"
            filter="url(#glow)"
            style={{ transition: 'all 0.6s cubic-bezier(0.4,0,0.2,1)' }}
          />
        )}

        {/* Center score */}
        <text x={cx} y={cy - 6} textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize={size * 0.22} fontWeight="800"
          fontFamily="'JetBrains Mono', monospace"
          style={{ transition: 'fill 0.4s' }}
        >
          {pct}
        </text>
        <text x={cx} y={cy + size * 0.14} textAnchor="middle"
          fill="rgba(240,244,255,0.45)" fontSize={size * 0.075} fontWeight="500"
          fontFamily="Inter, sans-serif"
        >
          CLS SCORE
        </text>

        {/* Tick marks at 0.33 and 0.66 */}
        {[0.33, 0.66].map((t) => {
          const td  = START_DEG + SWEEP_DEG * t;
          const tp  = polar(td);
          const tp2 = polar(td);
          const innerR = R - size * 0.07;
          const ip  = {
            x: cx + innerR * Math.cos((td * Math.PI) / 180),
            y: cy + innerR * Math.sin((td * Math.PI) / 180),
          };
          return (
            <line key={t} x1={ip.x} y1={ip.y} x2={tp.x} y2={tp.y}
              stroke="rgba(255,255,255,0.2)" strokeWidth={1.5} />
          );
        })}

        {/* Labels: LOW / HIGH */}
        <text x={p0.x - 4} y={p0.y + 14} textAnchor="middle"
          fill="var(--low)" fontSize={size * 0.062} fontWeight="700">LOW</text>
        <text x={fullEnd.x + 4} y={fullEnd.y + 14} textAnchor="middle"
          fill="var(--high)" fontSize={size * 0.062} fontWeight="700">HIGH</text>
      </svg>

      {/* State badge below gauge */}
      <div className={`badge badge-${clsState}`} style={{ fontSize: '0.85rem', padding: '5px 18px' }}>
        {clsState}
      </div>
    </div>
  );
}
