"use client";

import { cn, clamp, formatNumber } from "@/lib/utils";

interface GaugeProps {
  label: string;
  value: number | null;
  /** Min/max bound of the gauge sweep. */
  min: number;
  max: number;
  /** Optional zone tints painted under the gauge arc. */
  zones?: { from: number; to: number; color: string }[];
  unit?: string;
  size?: number;
  className?: string;
}

/**
 * Compact arc gauge used for RSI / MACD / Bollinger %B in the right rail.
 *
 * Pure SVG. The base track is a soft ivory hairline; zones are translucent
 * fills, the needle is a thin champagne-gold line.
 */
export const Gauge = ({
  label,
  value,
  min,
  max,
  zones,
  unit,
  size = 110,
  className,
}: GaugeProps) => {
  const sweep = 240;
  const startAngle = -210;
  const endAngle = startAngle + sweep;
  const radius = size / 2 - 10;
  const cx = size / 2;
  const cy = size / 2 + 4;

  const valueClamped = value == null ? null : clamp(value, min, max);
  const valueAngle =
    valueClamped == null
      ? null
      : startAngle + ((valueClamped - min) / (max - min)) * sweep;

  const polar = (angleDeg: number, r: number) => {
    const a = (angleDeg * Math.PI) / 180;
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r] as const;
  };

  const arcPath = (a0: number, a1: number, r: number) => {
    const [x0, y0] = polar(a0, r);
    const [x1, y1] = polar(a1, r);
    const large = a1 - a0 > 180 ? 1 : 0;
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
  };

  const tickAngles = [0, 0.5, 1].map((t) => startAngle + t * sweep);

  return (
    <div
      className={cn("flex flex-col items-center gap-1", className)}
      style={{ width: size }}
    >
      <svg width={size} height={size} className="overflow-visible">
        <path
          d={arcPath(startAngle, endAngle, radius)}
          stroke="rgba(242,234,211,0.10)"
          strokeWidth={5}
          fill="none"
          strokeLinecap="round"
        />
        {zones?.map((z, i) => {
          const a0 =
            startAngle + ((Math.max(min, z.from) - min) / (max - min)) * sweep;
          const a1 =
            startAngle + ((Math.min(max, z.to) - min) / (max - min)) * sweep;
          if (a1 <= a0) return null;
          return (
            <path
              key={i}
              d={arcPath(a0, a1, radius)}
              stroke={z.color}
              strokeOpacity={0.55}
              strokeWidth={5}
              fill="none"
              strokeLinecap="round"
            />
          );
        })}
        {tickAngles.map((a, i) => {
          const [x0, y0] = polar(a, radius - 4);
          const [x1, y1] = polar(a, radius + 3);
          return (
            <line
              key={i}
              x1={x0}
              y1={y0}
              x2={x1}
              y2={y1}
              stroke="rgba(242,234,211,0.25)"
              strokeWidth={1}
            />
          );
        })}
        {valueAngle != null &&
          (() => {
            const [nx, ny] = polar(valueAngle, radius - 4);
            return (
              <>
                <line
                  x1={cx}
                  y1={cy}
                  x2={nx}
                  y2={ny}
                  stroke="#E8C547"
                  strokeWidth={2}
                  strokeLinecap="round"
                />
                <circle cx={cx} cy={cy} r={3} fill="#E8C547" />
                <circle
                  cx={cx}
                  cy={cy}
                  r={6}
                  fill="none"
                  stroke="#E8C547"
                  strokeOpacity={0.2}
                />
              </>
            );
          })()}
      </svg>
      <div className="mono-num text-base text-gold leading-none -mt-3">
        {value == null ? "—" : `${formatNumber(value, 1)}${unit ?? ""}`}
      </div>
      <div className="text-[10px] uppercase tracking-[0.18em] text-ivory/50">
        {label}
      </div>
    </div>
  );
};
