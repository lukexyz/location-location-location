import { useRef } from "react";
import type { ReactNode } from "react";

import type { WhatIfScore } from "../lib/whatif";
import type { CandidateResult, ConstraintStatus, RouteBoundary } from "../types";

const LIMIT_TEXT: Record<ConstraintStatus, string> = {
  pass: "within limits", unknown: "limit unverified", fail: "outside hard limit",
};

interface RankedListProps {
  candidates: CandidateResult[];
  routeBoundary?: RouteBoundary;
  selectedId: string;
  sortMode: SortMode;
  whatIf?: Map<string, WhatIfScore>;
  onSort: (mode: SortMode) => void;
  onSelect: (id: string) => void;
  children?: ReactNode;
}

export type SortMode = "rank" | "score" | "confidence" | "name";

const SORT_MODES: SortMode[] = ["rank", "score", "confidence", "name"];

const PROFILE_WORD: Record<string, string> = { "driving-car": "drive", "cycling-regular": "cycle", "foot-walking": "walk" };

/** The four numbers that describe a search at a glance. */
export function searchStats(candidates: CandidateResult[], routeBoundary?: RouteBoundary): Array<{ key: string; value: string; label: string }> {
  const facts = candidates.reduce(
    (total, candidate) => total + candidate.categories.reduce((count, category) => count + category.metrics.length, 0) + candidate.informational_metrics.length,
    0,
  );
  const confidence = candidates.length ? Math.round(candidates.reduce((total, candidate) => total + candidate.confidence, 0) / candidates.length) : 0;
  const stats = [{ key: "places", value: String(candidates.length), label: candidates.length === 1 ? "place" : "places" }];
  if (routeBoundary?.duration_minutes) {
    const word = PROFILE_WORD[routeBoundary.travel_profile ?? ""] ?? "travel";
    stats.push({ key: "limit", value: `${routeBoundary.duration_minutes} min`, label: routeBoundary.type === "distance_proxy" ? `${word} · proxy` : word });
  }
  stats.push({ key: "confidence", value: `${confidence}%`, label: "confidence" });
  stats.push({ key: "facts", value: facts.toLocaleString("en-GB"), label: facts === 1 ? "fact" : "facts" });
  return stats;
}

export function RankedList({ candidates, routeBoundary, selectedId, sortMode, whatIf, onSort, onSelect, children }: RankedListProps) {
  const listRef = useRef<HTMLOListElement>(null);
  // Short enough to sit four abreast in the narrowest register without truncating.
  const sortLabels: Record<SortMode, string> = {
    rank: whatIf ? "What-if" : "Rank",
    score: "Score",
    confidence: "Confidence",
    name: "Name",
  };

  function moveFocus(index: number, key: string) {
    const buttons = listRef.current?.querySelectorAll<HTMLButtonElement>(".rank-entry");
    if (!buttons?.length) return;
    const target = key === "Home"
      ? 0
      : key === "End"
        ? buttons.length - 1
        : (index + (key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length;
    buttons[target].focus();
  }

  return (
    <aside className="rank-panel panel-cut" aria-labelledby="rank-heading">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">{whatIf ? "WHAT-IF ORDER" : "RESEARCHED RANK"}</span>
          <h2 id="rank-heading">Shortlist</h2>
        </div>
      </div>
      <div className="stat-tiles" role="group" aria-label="Search at a glance">
        {searchStats(candidates, routeBoundary).map((stat) => (
          <div key={stat.key}><strong>{stat.value}</strong><span>{stat.label}</span></div>
        ))}
      </div>
      <div className="sort-keys" role="group" aria-label="Sort candidates">
        <span className="sort-keys-label" aria-hidden="true">Sort</span>
        {SORT_MODES.map((mode) => (
          <button
            key={mode}
            type="button"
            className="sort-key"
            aria-pressed={sortMode === mode}
            onClick={() => onSort(mode)}
          >
            {sortLabels[mode]}
          </button>
        ))}
      </div>
      {children}
      <ol className="rank-list" ref={listRef}>
        {candidates.map((candidate, index) => {
          const selected = selectedId === candidate.id;
          const preview = whatIf?.get(candidate.id);
          return (
            <li key={candidate.id}>
              <button
                type="button"
                className="rank-entry"
                aria-pressed={selected}
                onClick={() => onSelect(candidate.id)}
                onKeyDown={(event) => {
                  if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
                    event.preventDefault();
                    moveFocus(index, event.key);
                  }
                }}
              >
                <span className="rank-number">{String(candidate.rank).padStart(2, "0")}</span>
                <span className="rank-copy">
                  <strong>{candidate.name}</strong>
                  <small className={`limit-line ${candidate.hard_constraints.status}`}>
                    {LIMIT_TEXT[candidate.hard_constraints.status]}
                    {candidate.score_coverage_percent < 100 ? ` · ${candidate.score_coverage_percent.toFixed(0)}% measured` : ""}
                    {preview ? ` · researched ${candidate.overall_score.toFixed(1)}` : ""}
                  </small>
                </span>
                <span className={`rank-score${preview ? " whatif" : ""}`}>
                  {(preview ? preview.overallScore : candidate.overall_score).toFixed(1)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      <div className="panel-footnote">
        {whatIf
          ? "Rank numbers stay researched; the order and bright scores are a what-if preview."
          : "Original rank always reflects hard-limit status, suitability, then confidence."}
      </div>
    </aside>
  );
}
