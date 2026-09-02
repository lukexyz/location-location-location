import { useRef } from "react";

import type { CandidateResult } from "../types";

interface RankedListProps {
  candidates: CandidateResult[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function RankedList({ candidates, selectedId, onSelect }: RankedListProps) {
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
        <span className="count-readout">{String(candidates.length).padStart(2, "0")}</span>
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
        Ranked by hard-limit status, suitability, then confidence.
      </div>
    </aside>
  );
}
