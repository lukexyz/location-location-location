import { useMemo, useRef, useState } from "react";

import demoData from "./data/demo-results.json";
import { Dossier } from "./components/Dossier";
import { MapView } from "./components/MapView";
import { RankedList } from "./components/RankedList";
import { compactDate } from "./lib/format";
import { parseResultBundle, ResultValidationError } from "./lib/validateResult";
import type { LoadState, ResearchResult } from "./types";

const demoResult = parseResultBundle(demoData);
const MAX_FILE_SIZE = 5 * 1024 * 1024;

export default function App() {
  const [result, setResult] = useState<ResearchResult>(demoResult);
  const [selectedId, setSelectedId] = useState(demoResult.candidates[0].id);
  const [loadState, setLoadState] = useState<LoadState>({
    kind: "demo",
    message: "Fictional demonstration data active",
  });
  const fileInput = useRef<HTMLInputElement>(null);
  const candidates = useMemo(
    () => [...result.candidates].sort((left, right) => left.rank - right.rank),
    [result],
  );
  const selected = candidates.find((candidate) => candidate.id === selectedId) ?? candidates[0];

  async function importResult(file: File | undefined) {
    if (!file) return;
    try {
      if (file.size > MAX_FILE_SIZE) {
        throw new ResultValidationError("That file exceeds the 5 MB local import limit.");
      }
      const next = parseResultBundle(JSON.parse(await file.text()));
      setResult(next);
      setSelectedId([...next.candidates].sort((a, b) => a.rank - b.rank)[0].id);
      setLoadState({ kind: "loaded", message: `${file.name} loaded in this tab only` });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to read that result bundle.";
      setLoadState({ kind: "error", message });
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function restoreDemo() {
    setResult(demoResult);
    setSelectedId(demoResult.candidates[0].id);
    setLoadState({ kind: "demo", message: "Fictional demonstration data active" });
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#candidate-register">Skip to candidate results</a>
      <MapView candidates={candidates} selectedId={selected.id} onSelect={setSelectedId} />

      <header className="instrument-header panel-cut">
        <div className="wordmark" aria-label="Location cubed">
          LOCATION<span>³</span>
        </div>
        <div className="system-title">
          <span>THE PLACE-FINDING INSTRUMENT</span>
          <strong>{result.run_id.replaceAll("-", " ")}</strong>
        </div>
        <div className={`load-state ${loadState.kind}`} role="status" aria-live="polite">
          <i aria-hidden="true" />
          <span>{loadState.message}</span>
        </div>
        <div className="header-actions">
          {loadState.kind !== "demo" && (
            <button className="utility-button" type="button" onClick={restoreDemo}>RESET DEMO</button>
          )}
          <button
            className="import-button"
            type="button"
            aria-describedby="local-import-note"
            onClick={() => fileInput.current?.click()}
          >
            <span>IMPORT</span>
            <strong>RESULT.JSON</strong>
          </button>
          <span id="local-import-note" className="visually-hidden">
            Opens a local JSON file. The result remains in this browser tab.
          </span>
          <input
            ref={fileInput}
            id="result-import"
            className="visually-hidden"
            data-testid="result-import"
            type="file"
            tabIndex={-1}
            aria-label="Choose result JSON file"
            accept="application/json,.json"
            onChange={(event) => void importResult(event.currentTarget.files?.[0])}
          />
        </div>
      </header>

      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        Selected candidate: {selected.name}, rank {selected.rank}, score {selected.overall_score.toFixed(1)}.
      </p>

      <main
        id="candidate-register"
        className="workspace"
        tabIndex={-1}
        aria-label="Candidate results and evidence"
      >
        <RankedList candidates={candidates} selectedId={selected.id} onSelect={setSelectedId} />
        <Dossier candidate={selected} />
      </main>

      <footer className="status-rail">
        <span><i className="status-light" /> VIEWER READY</span>
        <span>SCHEMA {result.schema_version} / SCORE {result.scoring_version}</span>
        <span>RESOLVED {compactDate(result.generated_at).toUpperCase()}</span>
        <span className="privacy-readout">LOCAL READ · NO RESULT UPLOAD · MAP TILES REMOTE</span>
      </footer>
    </div>
  );
}
