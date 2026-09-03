/**
 * The local progress feed: what a research or import command has actually done
 * so far. The viewer polls it only when served from the machine that runs the
 * command; on the public demo it never asks.
 */

export type ProgressStatus = "running" | "done" | "failed";
export type ProgressLevel = "info" | "warning" | "error";

export interface ProgressEvent {
  at: string;
  stage: string;
  message: string;
  level: ProgressLevel;
  counts?: Record<string, number>;
  provider?: string;
  cache?: "hit" | "miss";
}

export interface ProgressFeed {
  schema_version: "1";
  run_id: string;
  command: string;
  status: ProgressStatus;
  started_at: string;
  updated_at: string;
  events: ProgressEvent[];
  result_url: string | null;
  error?: string;
}

export class ProgressFeedError extends Error {}

const STATUSES = new Set<string>(["running", "done", "failed"]);
const LEVELS = new Set<string>(["info", "warning", "error"]);

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ProgressFeedError(`${path} must be an object`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, path: string): string {
  if (typeof value !== "string" || value.length === 0) throw new ProgressFeedError(`${path} must be a non-empty string`);
  return value;
}

export function parseProgressFeed(value: unknown): ProgressFeed {
  const feed = record(value, "progress");
  if (feed.schema_version !== "1") throw new ProgressFeedError("progress.schema_version must be 1");
  const status = text(feed.status, "progress.status");
  if (!STATUSES.has(status)) throw new ProgressFeedError("progress.status is unknown");
  if (!Array.isArray(feed.events)) throw new ProgressFeedError("progress.events must be an array");
  const events = feed.events.map((item, index): ProgressEvent => {
    const event = record(item, `progress.events[${index}]`);
    const level = text(event.level, `progress.events[${index}].level`);
    if (!LEVELS.has(level)) throw new ProgressFeedError(`progress.events[${index}].level is unknown`);
    const parsed: ProgressEvent = {
      at: text(event.at, `progress.events[${index}].at`),
      stage: text(event.stage, `progress.events[${index}].stage`),
      message: text(event.message, `progress.events[${index}].message`),
      level: level as ProgressLevel,
    };
    if (event.counts !== undefined) {
      const counts = record(event.counts, `progress.events[${index}].counts`);
      parsed.counts = Object.fromEntries(Object.entries(counts).map(([key, count]) => {
        if (typeof count !== "number" || !Number.isFinite(count)) {
          throw new ProgressFeedError(`progress.events[${index}].counts.${key} must be a number`);
        }
        return [key, count];
      }));
    }
    if (event.provider !== undefined) parsed.provider = text(event.provider, `progress.events[${index}].provider`);
    if (event.cache !== undefined) {
      if (event.cache !== "hit" && event.cache !== "miss") throw new ProgressFeedError(`progress.events[${index}].cache must be hit or miss`);
      parsed.cache = event.cache;
    }
    return parsed;
  });
  if (feed.result_url !== null && feed.result_url !== undefined && typeof feed.result_url !== "string") {
    throw new ProgressFeedError("progress.result_url must be a string or null");
  }
  const parsed: ProgressFeed = {
    schema_version: "1",
    run_id: text(feed.run_id, "progress.run_id"),
    command: text(feed.command, "progress.command"),
    status: status as ProgressStatus,
    started_at: text(feed.started_at, "progress.started_at"),
    updated_at: text(feed.updated_at, "progress.updated_at"),
    events,
    result_url: typeof feed.result_url === "string" ? feed.result_url : null,
  };
  if (feed.error !== undefined) parsed.error = text(feed.error, "progress.error");
  return parsed;
}

/** Only a viewer served from this machine may ask for a feed; the public demo never does. */
export function isLocalViewer(location: { hostname: string; protocol: string }): boolean {
  if (location.protocol === "file:") return false;
  return ["localhost", "127.0.0.1", "[::1]", "::1"].includes(location.hostname);
}

/** A caption per stage: the whimsy sits on top of the real event, never instead of it. */
export const STAGE_CAPTIONS: Record<string, string> = {
  boundary: "Drawing the fence",
  discovery: "Knocking on doors",
  measure: "Pacing fifteen-minute walks",
  score: "Weighing what matters",
  write: "Sealing the envelope",
  import: "Filing cited evidence",
};

export const WORKING_QUIPS: ReadonlyArray<string> = [
  "Counting cafés, not calories",
  "Asking the map nicely",
  "Refusing to invent a number",
  "Checking the last train home",
  "Not scraping any portals",
  "Reading the small print on every source",
  "Rounding your origin so nobody can find your door",
];

export function stageCaption(stage: string): string {
  return STAGE_CAPTIONS[stage] ?? stage.replaceAll("_", " ");
}

export function latestEvent(feed: ProgressFeed): ProgressEvent | undefined {
  return feed.events[feed.events.length - 1];
}
