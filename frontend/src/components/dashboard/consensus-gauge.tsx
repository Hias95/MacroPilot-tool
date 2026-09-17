"use client";

import { useEffect, useRef, useState } from "react";
import { clampScore, zoneForScore } from "@/lib/score";
import { cn } from "@/lib/utils";

/* Geometrie: Halbkreis von links (180 Grad) ueber oben nach rechts (0 Grad). */
const CX = 120;
const CY = 126;
const R = 92;
const HALF = Math.PI * R; // Bogenlaenge des Halbkreises

function polar(deg: number, r: number) {
  const a = (deg * Math.PI) / 180;
  return { x: CX + r * Math.cos(a), y: CY - r * Math.sin(a) };
}

const ARC = (() => {
  const s = polar(180, R);
  const e = polar(0, R);
  return `M ${s.x} ${s.y} A ${R} ${R} 0 0 1 ${e.x} ${e.y}`;
})();

/* Zonengrenzen (Quantile des Rangs), nicht gleichmaessig. */
const TICKS = [0, 10, 30, 70, 90, 100];

/** Bogenstueck zwischen zwei Score-Werten, gleiche Drehrichtung wie die Nadel. */
function arcBetween(from: number, to: number, r: number) {
  const s = polar(180 - from * 1.8, r);
  const e = polar(180 - to * 1.8, r);
  return `M ${s.x} ${s.y} A ${r} ${r} 0 0 1 ${e.x} ${e.y}`;
}

interface Props {
  score: number;
  /** Bestaetigte Zone vom Backend; ohne Angabe wird sie aus dem Score abgeleitet. */
  zone?: { label: string; color: string; min?: number; max?: number };
  /** Zone dieser Woche, solange sie von der bestaetigten abweicht. Loest den Widerspruch auf,
   *  dass die Nadel im gruenen Feld steht, waehrend darunter noch das alte Zonenwort haengt. */
  pending?: { label: string; color: string } | null;
  className?: string;
}

export function ConsensusGauge({ score, zone: zoneProp, pending, className }: Props) {
  const target = clampScore(score);
  const [shown, setShown] = useState(0);
  const fromRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    const start = performance.now();
    const duration = 1100;
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(Math.round(from + (target - from) * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);

  const zone = zoneProp ?? zoneForScore(target);
  const dashOffset = HALF * (1 - shown / 100);
  const needleDeg = shown * 1.8;

  return (
    <div className={cn("relative mx-auto w-full max-w-[440px]", className)}>
      <svg
        viewBox="-8 0 256 196"  /* Hoehe reicht bis unter die Zeile der schwebenden Zone (y = CY + 64) */
        className="w-full"
        role="img"
        aria-label={
          `Consensus Score ${target} von 100, bestätigte Zone ${zone.label}` +
          (pending ? `, diese Woche bereits ${pending.label}` : "")
        }
      >
        <defs>
          <linearGradient id="gauge-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="oklch(0.68 0.2 25)" />
            <stop offset="50%" stopColor="oklch(0.82 0.16 75)" />
            <stop offset="100%" stopColor="oklch(0.78 0.18 150)" />
          </linearGradient>
          <filter id="gauge-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Hintergrund-Spur */}
        <path d={ARC} fill="none" stroke="oklch(1 0 0 / 7%)" strokeWidth={12} strokeLinecap="round" />

        {/* Wert-Bogen, wird ueber dashoffset freigelegt */}
        <path
          d={ARC}
          fill="none"
          stroke="url(#gauge-grad)"
          strokeWidth={12}
          strokeLinecap="round"
          strokeDasharray={HALF}
          strokeDashoffset={dashOffset}
          filter="url(#gauge-glow)"
        />

        {/* Feld der bestaetigten Zone, innen gezeichnet: zeigt, worauf sich das Zonenwort bezieht, und macht
            sichtbar, dass die Nadel bereits daneben steht. Aussen waere es vom Hauptbogen verdeckt. */}
        {zone.min != null && zone.max != null ? (
          <path
            d={arcBetween(zone.min, zone.max, R - 13)}
            fill="none"
            stroke={zone.color}
            strokeWidth={3}
            strokeLinecap="butt"
            opacity={0.85}
          />
        ) : null}

        {/* Skala */}
        {TICKS.map((t) => {
          const a = 180 - t * 1.8;
          const p1 = polar(a, R + 11);
          const p2 = polar(a, R + 15);
          const pl = polar(a, R + 24);
          return (
            <g key={t}>
              <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="oklch(1 0 0 / 28%)" strokeWidth={1} />
              <text
                x={pl.x}
                y={pl.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={7}
                fill="oklch(1 0 0 / 45%)"
                className="font-mono"
              >
                {t}
              </text>
            </g>
          );
        })}

        {/* Nadel: zeigt initial nach links (Score 0) und dreht im Uhrzeigersinn */}
        <g
          style={{
            transform: `rotate(${needleDeg}deg)`,
            transformOrigin: `${CX}px ${CY}px`,
            transformBox: "view-box",
          }}
        >
          <line
            x1={CX}
            y1={CY}
            x2={CX - (R - 20)}
            y2={CY}
            stroke="oklch(0.97 0 0)"
            strokeWidth={2.5}
            strokeLinecap="round"
          />
        </g>
        <circle cx={CX} cy={CY} r={5.5} fill="oklch(0.97 0 0)" />
        <circle cx={CX} cy={CY} r={2} fill="oklch(0.15 0.008 260)" />

        {/* Zahl + Zone unter der Nabe */}
        <text
          x={CX}
          y={CY + 36}
          textAnchor="middle"
          fontSize={32}
          fontWeight={600}
          fill="currentColor"
          className="font-heading tabular-nums"
          style={{ letterSpacing: "-0.02em" }}
        >
          {shown}
        </text>
        <text
          x={CX}
          y={CY + 52}
          textAnchor="middle"
          fontSize={9}
          fontWeight={500}
          fill={zone.color}
          style={{ letterSpacing: "0.12em", textTransform: "uppercase" }}
        >
          {zone.label}
        </text>
        {pending ? (
          <text
            x={CX}
            y={CY + 64}
            textAnchor="middle"
            fontSize={7.5}
            fill={pending.color}
            style={{ letterSpacing: "0.1em", textTransform: "uppercase" }}
          >
            {`diese Woche ${pending.label}`}
          </text>
        ) : null}
      </svg>
    </div>
  );
}
