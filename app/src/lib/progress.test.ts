import done from "../test/fixtures/progress-done.json";
import running from "../test/fixtures/progress-running.json";
import { ProgressFeedError, isLocalViewer, latestEvent, parseProgressFeed, stageCaption } from "./progress";

describe("progress feed", () => {
  it("accepts the running and finished fixtures and keeps their real counts", () => {
    const feed = parseProgressFeed(running);
    expect(feed.status).toBe("running");
    expect(feed.events).toHaveLength(2);
    expect(feed.events[1].counts).toEqual({ candidates: 17, observations: 68 });
    expect(feed.events[1].cache).toBe("miss");
    expect(latestEvent(feed)?.stage).toBe("discovery");
    const finished = parseProgressFeed(done);
    expect(finished.status).toBe("done");
    expect(finished.result_url).toBe("runs/my-search/results.json");
  });

  it.each([
    ["a wrong schema", (feed: Record<string, unknown>) => { feed.schema_version = "2"; }],
    ["an unknown status", (feed: Record<string, unknown>) => { feed.status = "paused"; }],
    ["a non-array event list", (feed: Record<string, unknown>) => { feed.events = {}; }],
    ["an unknown level", (feed: Record<string, unknown>) => { (feed.events as Array<Record<string, unknown>>)[0].level = "loud"; }],
    ["a stale cache flag", (feed: Record<string, unknown>) => { (feed.events as Array<Record<string, unknown>>)[1].cache = "stale"; }],
    ["a non-numeric count", (feed: Record<string, unknown>) => { (feed.events as Array<Record<string, unknown>>)[1].counts = { candidates: "many" }; }],
    ["a numeric result url", (feed: Record<string, unknown>) => { feed.result_url = 3; }],
  ])("rejects %s", (_name, mutate) => {
    const invalid = structuredClone(running) as unknown as Record<string, unknown>;
    mutate(invalid);
    expect(() => parseProgressFeed(invalid)).toThrow(ProgressFeedError);
  });

  it("only treats a loopback page as a local viewer", () => {
    expect(isLocalViewer({ hostname: "127.0.0.1", protocol: "http:" })).toBe(true);
    expect(isLocalViewer({ hostname: "localhost", protocol: "http:" })).toBe(true);
    expect(isLocalViewer({ hostname: "lukexyz.github.io", protocol: "https:" })).toBe(false);
    expect(isLocalViewer({ hostname: "", protocol: "file:" })).toBe(false);
  });

  it("captions every known stage and falls back to the stage name", () => {
    expect(stageCaption("discovery")).toBe("Knocking on doors");
    expect(stageCaption("import")).toBe("Filing cited evidence");
    expect(stageCaption("something_new")).toBe("something new");
  });
});
