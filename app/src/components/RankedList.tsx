import { useRef } from "react";
import type { ReactNode } from "react";

import type { WhatIfScore } from "../lib/whatif";
import type { CandidateResult, ConstraintStatus } from "../types";

const LIMIT_TEXT: Record<ConstraintStatus, string> = {
  pass: "within limits", unknown: "limit unverified", fail: "outside hard limit",
};

interface RankedListProps {
  candidates: CandidateResult[];
  selectedId: string;
  sortMode: SortMode;
  whatIf?: Map<string, WhatIfScore>;
  onSort: (mode: SortMode) => void;
  onSelect: (id: string) => void;
  children?: ReactNode;
}

export type SortMode = "rank" | "score" | "confidence" | "name";

export function RankedList({ candidates, selectedId, sortMode, whatIf, onSort, onSelect, children }: RankedListProps) {
  const listRef = useRef<HTMLOListElement>(null);

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
          <span className="eyebrow">{whatIf ? "WHAT-IF ORDER" : "RESOLVED FIELD"}</span>
          <h2 id="rank-heading">Candidate register</h2>
        </div>
        <div className="rank-controls">
          <span className="count-readout">{String(candidates.length).padStart(2, "0")}</span>
          <label>
            <span>Sort</span>
            <select
              aria-label="Sort candidates"
              value={sortMode}
              onChange={(event) => onSort(event.currentTarget.value as SortMode)}
            >
              <option value="rank">{whatIf ? "What-if" : "Recommended"}</option>
              <option value="score">Suitability</option>
              <option value="confidence">Confidence</option>
              <option value="name">Name</option>
            </select>
          </label>
        </div>
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
                  <small>
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
