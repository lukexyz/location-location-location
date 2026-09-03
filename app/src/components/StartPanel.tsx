import { useEffect, useRef, useState } from "react";

import {
  AGENTS, NEXT_STEPS, PRIVACY_NOTES, REPOSITORY_URL, REQUIREMENTS, SHELLS, WORKFLOW_URL,
  bootstrapCommand, detectShell,
} from "../lib/onboarding";
import type { Agent, Shell } from "../lib/onboarding";

interface BannerProps {
  onOpen: () => void;
}

/** The front door, shown only while the demonstration bundle is active. */
export function StartBanner({ onOpen }: BannerProps) {
  return (
    <section className="start-banner panel-cut" aria-labelledby="start-banner-heading">
      <div className="start-banner-copy">
        <span className="eyebrow">SAMPLE RUN / REAL TOWNS, SYNTHETIC EVIDENCE</span>
        <h2 id="start-banner-heading">This is what a finished search looks like. Yours runs on your machine, with your criteria.</h2>
      </div>
      <button className="start-button" type="button" onClick={onOpen}>
        <strong>RUN YOUR OWN SEARCH</strong>
        <span>ONE LINE · YOUR AGENT · FREE</span>
      </button>
    </section>
  );
}

interface DialogProps {
  onClose: () => void;
}

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function StartDialog({ onClose }: DialogProps) {
  const [agent, setAgent] = useState<Agent>("claude");
  const [shell, setShell] = useState<Shell>(() => detectShell(typeof navigator === "undefined" ? undefined : navigator.platform));
  const [copied, setCopied] = useState<string | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const command = bootstrapCommand(agent, shell);
  const chosen = AGENTS.find((item) => item.id === agent)!;

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    element.querySelector<HTMLElement>("h2")?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !element) return;
      const focusable = Array.from(element.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === element.querySelector("h2"))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(null), 2200);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied("Copied to the clipboard");
    } catch {
      setCopied("Copy failed; select the line and copy it by hand");
    }
  }

  return (
    <div className="start-backdrop" onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div ref={dialog} className="start-dialog panel-cut" role="dialog" aria-modal="true" aria-labelledby="start-dialog-heading">
        <header className="start-dialog-heading">
          <div>
            <span className="eyebrow">YOUR OWN SEARCH / RUNS LOCALLY</span>
            <h2 id="start-dialog-heading" tabIndex={-1}>Run your own search</h2>
          </div>
          <button className="utility-button" type="button" onClick={onClose} aria-label="Close">CLOSE</button>
        </header>
        <p className="start-intro">
          The demo shows a finished result on real towns with synthetic evidence. Your search runs on your own machine:
          your coding agent gathers cited evidence on the subscription you already have, and deterministic Python scores it.
          Nothing is uploaded.
        </p>

        <div className="start-tabs" role="tablist" aria-label="Choose your agent">
          {AGENTS.map((item) => (
            <button
              key={item.id}
              id={`agent-tab-${item.id}`}
              className="sort-key"
              type="button"
              role="tab"
              aria-selected={agent === item.id}
              aria-controls="start-command-panel"
              onClick={() => setAgent(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="start-shells" role="group" aria-label="Choose your shell">
          {SHELLS.map((item) => (
            <button
              key={item.id}
              className="sort-key"
              type="button"
              aria-pressed={shell === item.id}
              onClick={() => setShell(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <section id="start-command-panel" role="tabpanel" aria-labelledby={`agent-tab-${agent}`} className="start-command">
          <span className="eyebrow">PASTE INTO A TERMINAL</span>
          <pre data-testid="bootstrap-command"><code>{command}</code></pre>
          <div className="start-command-actions">
            <button className="import-button" type="button" aria-label="Copy the command" onClick={() => void copyCommand()}>
              <span>COPY</span>
              <strong>ONE LINE</strong>
            </button>
            <span className="start-copied" role="status" aria-live="polite">{copied ?? ""}</span>
          </div>
          <p className="start-note">
            Once inside, the skill is <code>{chosen.invocation}</code>. {REQUIREMENTS}
          </p>
        </section>

        <div className="start-columns">
          <section aria-labelledby="start-next-heading">
            <h3 id="start-next-heading">What happens next</h3>
            <ol>
              {NEXT_STEPS.map((step) => <li key={step}>{step}</li>)}
            </ol>
          </section>
          <section aria-labelledby="start-private-heading">
            <h3 id="start-private-heading">What stays private</h3>
            <ul>
              {PRIVACY_NOTES.map((note) => <li key={note}>{note}</li>)}
            </ul>
          </section>
        </div>

        <footer className="start-dialog-footer">
          <a href={WORKFLOW_URL} rel="noreferrer" target="_blank">Read the full research workflow ↗</a>
          <a href={REPOSITORY_URL} rel="noreferrer" target="_blank">Source on GitHub ↗</a>
        </footer>
      </div>
    </div>
  );
}
