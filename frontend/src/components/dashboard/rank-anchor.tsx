"use client";

import type { ConsensusHistoryPoint } from "@/lib/api";

/**
 * J1: Eine Zahl ohne Vergleich ist keine Information.
 *
 * "65" allein liest sich wie eine Schulnote. Erst der Blick zurück macht daraus eine Aussage: War es vor
 * einem Monat höher oder tiefer, und wo stand es vor einem Jahr. Das steht bisher nur im Verlaufschart, und
 * einen Chart liest der Einsteiger nicht.
 */
export function RankAnchor({ points }: { points: ConsensusHistoryPoint[] | null | undefined }) {
  if (!points || points.length < 53) return null;
  const monthAgo = points[points.length - 5]?.score;
  const yearAgo = points[points.length - 53]?.score;
  if (monthAgo == null || yearAgo == null) return null;

  return (
    <p className="text-sm text-muted-foreground text-pretty">
      Zum Vergleich: vor einem Monat <span className="tabular-nums text-foreground/90">{monthAgo}</span>, vor einem Jahr{" "}
      <span className="tabular-nums text-foreground/90">{yearAgo}</span>.
    </p>
  );
}
