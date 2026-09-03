import { useCallback, useMemo, useRef, useState } from "react";

import demoData from "./data/demo-results.json";
import { Dossier } from "./components/Dossier";
import { MapView } from "./components/MapView";
import { ProgressModal } from "./components/ProgressModal";
import { RankedList } from "./components/RankedList";
import { StartBanner, StartDialog } from "./components/StartPanel";
import type { SortMode } from "./components/RankedList";
import { TunePanel } from "./components/TunePanel";
import { compactDate } from "./lib/format";
import { isLocalViewer } from "./lib/progress";
import { useProgressFeed } from "./lib/useProgressFeed";
import { MAX_CANDIDATES, parseResultBundle, ResultValidationError } from "./lib/validateResult";
import { deriveBaseline, orderWhatIf, scoreWhatIf, weightsDiffer } from "./lib/whatif";
import type { WeightMap, WhatIfScore } from "./lib/whatif";
import type { LoadState, ResearchResult } from "./types";

const demoResult = parseResultBundle(demoData);
// The demo weighs about 14 KB per candidate; 25 MB leaves headroom for the
// 1,000-candidate limit so the two limits cannot contradict each other.
export const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;
const DEMO_STATE: LoadState = {
  kind: "demo",
  message: "Sample data: real towns, synthetic evidence",
};
// The feed is polled only from a loopback page (the local serve command or the
// dev server), never from the public demo, and never inside unit tests.
const LOCAL_VIEWER = typeof window !== "undefined" && isLocalViewer(window.location) && import.meta.env.MODE !== "test";

/** A run id reads as a title: hyphens become spaces and the first letter is capitalised. */
function runTitle(runId: string): string {
  const words = runId.replaceAll("-", " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export default function App() {
  const [result, setResult] = useState<ResearchResult>(demoResult);
  const [fieldSerial, setFieldSerial] = useState(0);
  const [selectedId, setSelectedId] = useState(demoResult.candidates[0].id);
  const [sortMode, setSortMode] = useState<SortMode>("rank");
  const [weights, setWeights] = useState<WeightMap>({});
  const [categoryWeights, setCategoryWeights] = useState<WeightMap>({});
  const [loadState, setLoadState] = useState<LoadState>(DEMO_STATE);
  const [startOpen, setStartOpen] = useState(false);
  const progress = useProgressFeed(LOCAL_VIEWER);
  const [dismissedRun, setDismissedRun] = useState<string | null>(null);
  const [loadingResult, setLoadingResult] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const baseline = useMemo(() => deriveBaseline(result), [result]);
  const whatIfActive = weightsDiffer(weights, baseline, categoryWeights);
  const whatIf = useMemo(() => {
    if (!whatIfActive) return undefined;
    return new Map<string, WhatIfScore>(
      result.candidates.map((candidate) => [candidate.id, scoreWhatIf(candidate, weights, baseline, categoryWeights)]),
    );
  }, [result, weights, categoryWeights, baseline, whatIfActive]);
  const candidates = useMemo(() => {
    const ordered = [...result.candidates];
    if (sortMode === "name") return ordered.sort((left, right) => left.name.localeCompare(right.name));
    if (sortMode === "confidence") {
      return ordered.sort((left, right) => right.confidence - left.confidence || left.rank - right.rank);
    }
    if (whatIf) {
      const position = new Map(orderWhatIf([...whatIf.values()]).map((score, index) => [score.id, index]));
      return ordered.sort((left, right) => position.get(left.id)! - position.get(right.id)!);
    }
    if (sortMode === "score") {
      return ordered.sort((left, right) => right.overall_score - left.overall_score || left.rank - right.rank);
    }
    return ordered.sort((left, right) => left.rank - right.rank);
  }, [result, sortMode, whatIf]);
  const selected = candidates.find((candidate) => candidate.id === selectedId) ?? candidates[0];
  const demoActive = result === demoResult;
  const closeStart = useCallback(() => {
    setStartOpen(false);
    // Hand focus back to the door the visitor came through.
    window.requestAnimationFrame(() => document.querySelector<HTMLElement>(".start-button")?.focus());
  }, []);

  function loadBundle(next: ResearchResult, state: LoadState) {
    setStartOpen(false);
    setResult(next);
    setFieldSerial((serial) => serial + 1);
    setWeights({});
    setCategoryWeights({});
    setSortMode("rank");
    setSelectedId([...next.candidates].sort((a, b) => a.rank - b.rank)[0].id);
    setLoadState(state);
  }

  async function importResult(file: File | undefined) {
    if (!file) return;
    try {
      if (file.size > MAX_FILE_SIZE) {
        throw new ResultValidationError(
          `That file exceeds the ${MAX_FILE_SIZE_MB} MB local import limit; the viewer also accepts at most ${MAX_CANDIDATES.toLocaleString("en-GB")} candidates per bundle.`,
        );
      }
      const next = parseResultBundle(JSON.parse(await file.text()));
      loadBundle(next, { kind: "loaded", message: `${file.name} loaded in this tab only` });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to read that result bundle.";
      setLoadState({ kind: "error", message });
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function restoreDemo() {
    loadBundle(demoResult, DEMO_STATE);
  }

  async function loadServedResult(url: string) {
    setLoadingResult(true);
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new ResultValidationError(`The local serve returned HTTP ${response.status} for ${url}.`);
      }
      const next = parseResultBundle(await response.json());
      loadBundle(next, { kind: "loaded", message: `${next.run_id} loaded from the local run; it stays in this tab` });
      setDismissedRun(progress?.started_at ?? null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to read the finished result.";
      setLoadState({ kind: "error", message });
    } finally {
      setLoadingResult(false);
    }
  }

  const progressVisible = progress !== undefined && dismissedRun !== progress.started_at && !startOpen;

  function restoreImportance() {
    setWeights({});
    setCategoryWeights({});
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#candidate-register">Skip to candidate results</a>
      <MapView
        candidates={result.candidates}
        fieldKey={`${result.run_id}:${result.generated_at}:${fieldSerial}`}
        routeBoundary={result.route_boundary}
        selectedId={selected.id}
        onSelect={setSelectedId}
      />

      <header className="instrument-header panel-cut">
        <div className="wordmark" aria-label="Location cubed">
          LOCATION<span>³</span>
        </div>
        <div className="system-title">
          <span>WHERE TO LIVE, WITH RECEIPTS</span>
          <strong>{runTitle(result.run_id)}</strong>
        </div>
        <div className={`load-state ${loadState.kind}`} role="status" aria-live="polite">
          <i aria-hidden="true" />
          <span title={loadState.message}>{loadState.message}</span>
        </div>
        <div className="header-actions">
          {!demoActive && (
            <button className="utility-button" type="button" onClick={restoreDemo}>Reset demo</button>
          )}
          <button
            className="import-button"
            type="button"
            aria-describedby="local-import-note"
            onClick={() => fileInput.current?.click()}
          >
            <span>IMPORT</span>
            <strong>result.json</strong>
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

      {demoActive && <StartBanner onOpen={() => setStartOpen(true)} />}

      <p className="visually-hidden" aria-live="polite" aria-atomic="true">
        Selected candidate: {selected.name}, rank {selected.rank}, score {selected.overall_score.toFixed(1)}.
        {whatIf ? ` What-if score ${whatIf.get(selected.id)!.overallScore.toFixed(1)}.` : ""}
      </p>

      <main
        id="candidate-register"
        className="workspace"
        tabIndex={-1}
        aria-label="Candidate results and evidence"
      >
        <RankedList
          candidates={candidates}
          selectedId={selected.id}
          sortMode={sortMode}
          whatIf={whatIf}
          onSort={setSortMode}
          onSelect={setSelectedId}
        >
          <TunePanel
            baseline={baseline}
            weights={weights}
            categoryWeights={categoryWeights}
            onChange={setWeights}
            onCategoryChange={setCategoryWeights}
            onReset={restoreImportance}
          />
        </RankedList>
        <Dossier
          candidate={selected}
          routeBoundary={result.route_boundary}
          whatIf={whatIf?.get(selected.id)}
        />
      </main>

      <footer className="status-rail">
        <span><i className="status-light" /> Ready</span>
        <span>Schema {result.schema_version} · scoring {result.scoring_version}</span>
        <span>Researched {compactDate(result.generated_at)}</span>
        {whatIf && <span className="whatif-readout">What-if preview · researched ranks kept</span>}
        <span className="privacy-readout">Runs in your browser · nothing uploaded · map tiles from OpenStreetMap</span>
      </footer>

      {startOpen && <StartDialog onClose={closeStart} />}
      {progressVisible && (
        <ProgressModal
          feed={progress}
          loading={loadingResult}
          onLoad={(url) => void loadServedResult(url)}
          onDismiss={() => setDismissedRun(progress.started_at)}
        />
      )}
    </div>
  );
}
