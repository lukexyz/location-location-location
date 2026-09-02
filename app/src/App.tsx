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
      <a className="skip-link" href="#candidate-register">Skip to candidates</a>
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
          <label className="import-button" htmlFor="result-import">
            <span>IMPORT</span>
            <strong>RESULT.JSON</strong>
          </label>
          <input
            ref={fileInput}
            id="result-import"
            className="visually-hidden"
            data-testid="result-import"
            type="file"
            accept="application/json,.json"
            onChange={(event) => void importResult(event.currentTarget.files?.[0])}
          />
        </div>
      </header>

      <div id="candidate-register">
        <RankedList candidates={candidates} selectedId={selected.id} onSelect={setSelectedId} />
      </div>
      <Dossier candidate={selected} />

      <footer className="status-rail">
        <span><i className="status-light" /> VIEWER READY</span>
        <span>SCHEMA {result.schema_version} / SCORE {result.scoring_version}</span>
        <span>RESOLVED {compactDate(result.generated_at).toUpperCase()}</span>
        <span className="privacy-readout">LOCAL READ · NO RESULT UPLOAD · MAP TILES REMOTE</span>
      </footer>
    </div>
  );
}
