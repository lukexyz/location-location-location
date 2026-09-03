import { useEffect, useState } from "react";

import { compactDate } from "../lib/format";
import { WORKING_QUIPS, latestEvent, stageCaption } from "../lib/progress";
import type { ProgressEvent, ProgressFeed } from "../lib/progress";

interface Props {
  feed: ProgressFeed;
  onLoad: (url: string) => void;
  onDismiss: () => void;
  loading?: boolean;
}

const QUIP_INTERVAL_MS = 2600;

function clock(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function countsLine(counts: Record<string, number> | undefined): string {
  if (!counts) return "";
  return Object.entries(counts).map(([key, value]) => `${value.toLocaleString("en-GB")} ${key.replaceAll("_", " ")}`).join(" · ");
}

function EventRow({ event }: { event: ProgressEvent }) {
  const counts = countsLine(event.counts);
  return (
    <li className={`progress-event ${event.level}`}>
      <span className="progress-time">{clock(event.at)}</span>
      <div className="progress-body">
        <span className="progress-stage">{stageCaption(event.stage)}</span>
        <p>{event.message}</p>
        {(counts || event.provider || event.cache) && (
          <small>
            {counts}
            {event.provider ? `${counts ? " · " : ""}${event.provider}` : ""}
            {event.cache ? ` · cache ${event.cache}` : ""}
          </small>
        )}
      </div>
    </li>
  );
}

/** What the run is doing right now, from the feed the command writes. */
export function ProgressModal({ feed, onLoad, onDismiss, loading = false }: Props) {
  const [quip, setQuip] = useState(0);
  const running = feed.status === "running";
  const latest = latestEvent(feed);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setQuip((index) => (index + 1) % WORKING_QUIPS.length), QUIP_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [running]);

  const headline = feed.status === "done"
    ? "Research complete"
    : feed.status === "failed"
      ? "Research stopped"
      : latest ? stageCaption(latest.stage) : "Starting up";

  return (
    <div className="start-backdrop progress-backdrop">
      <section className={`start-dialog progress-dialog panel-cut ${feed.status}`} role="dialog" aria-modal="true" aria-labelledby="progress-heading" aria-describedby="progress-status">
        <header className="start-dialog-heading">
          <div>
            <span className="eyebrow">LOCAL RUN / {feed.command.toUpperCase()} / {feed.run_id}</span>
            <h2 id="progress-heading">{headline}</h2>
          </div>
          <div className={`plumbob ${feed.status}`} aria-hidden="true"><i /></div>
        </header>
        <p id="progress-status" className="progress-quip" role="status" aria-live="polite">
          {running
            ? `${WORKING_QUIPS[quip]}. Started ${compactDate(feed.started_at)}; ${feed.events.length} ${feed.events.length === 1 ? "step" : "steps"} so far.`
            : feed.status === "done"
              ? `Finished with ${feed.events.length} recorded steps. Nothing left this machine that the preview did not list.`
              : `Stopped: ${feed.error ?? "the command reported a failure"}. Cache progress is kept; rerun the identical command to resume.`}
        </p>
        <ol className="progress-events" aria-label="Recorded steps" tabIndex={0}>
          {feed.events.map((event, index) => <EventRow key={`${event.at}-${index}`} event={event} />)}
          {running && (
            <li className="progress-event pending" aria-hidden="true">
              <span className="progress-time">now</span>
              <div className="progress-body"><span className="progress-stage">working…</span></div>
            </li>
          )}
        </ol>
        <footer className="start-dialog-footer progress-actions">
          {feed.status === "done" && feed.result_url && (
            <button className="start-button" type="button" disabled={loading} onClick={() => onLoad(feed.result_url!)}>
              <strong>{loading ? "LOADING…" : "LOAD THIS RESULT"}</strong>
              <span>PRIVATE · THIS TAB ONLY</span>
            </button>
          )}
          <button className="utility-button" type="button" onClick={onDismiss}>
            {running ? "HIDE WHILE IT WORKS" : "DISMISS"}
          </button>
        </footer>
      </section>
    </div>
  );
}
