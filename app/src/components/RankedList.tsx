import { useRef } from "react";

import type { CandidateResult } from "../types";

interface RankedListProps {
  candidates: CandidateResult[];
  selectedId: string;
  sortMode: SortMode;
  onSort: (mode: SortMode) => void;
  onSelect: (id: string) => void;
}

export type SortMode = "rank" | "score" | "confidence" | "name";

export function RankedList({ candidates, selectedId, sortMode, onSort, onSelect }: RankedListProps) {
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
          <span className="eyebrow">RESOLVED FIELD</span>
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
              <option value="rank">Recommended</option>
              <option value="score">Suitability</option>
              <option value="confidence">Confidence</option>
              <option value="name">Name</option>
            </select>
          </label>
        </div>
      </div>
      <ol className="rank-list" ref={listRef}>
        {candidates.map((candidate, index) => {
          const selected = selectedId === candidate.id;
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
                    {candidate.hard_constraints.passed ? "within limits" : "outside hard limit"}
                  </small>
                </span>
                <span className="rank-score">{candidate.overall_score.toFixed(1)}</span>
              </button>
            </li>
          );
        })}
      </ol>
      <div className="panel-footnote">
        Original rank always reflects hard-limit status, suitability, then confidence.
      </div>
    </aside>
  );
}
