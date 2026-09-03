import { useEffect, useState } from "react";

import { parseProgressFeed } from "./progress";
import type { ProgressFeed } from "./progress";

export const PROGRESS_URL = "./progress.json";
export const PROGRESS_INTERVAL_MS = 2000;

/**
 * Poll the local progress feed. A missing feed, an HTML fallback from a dev
 * server, or an unparsable document all mean "no run in progress" and are
 * silently ignored; the hook only ever surfaces a feed it could validate.
 */
export function useProgressFeed(enabled: boolean, intervalMs = PROGRESS_INTERVAL_MS): ProgressFeed | undefined {
  const [feed, setFeed] = useState<ProgressFeed | undefined>(undefined);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let timer: number | undefined;
    const controller = new AbortController();

    async function poll() {
      try {
        const response = await fetch(PROGRESS_URL, { cache: "no-store", signal: controller.signal });
        const type = response.headers.get("content-type") ?? "";
        if (response.ok && type.includes("json")) {
          const next = parseProgressFeed(await response.json());
          if (!cancelled) setFeed(next);
        } else if (!cancelled) {
          setFeed(undefined);
        }
      } catch {
        if (!cancelled) setFeed(undefined);
      }
      if (!cancelled) timer = window.setTimeout(() => void poll(), intervalMs);
    }

    void poll();
    return () => {
      cancelled = true;
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [enabled, intervalMs]);

  return feed;
}
