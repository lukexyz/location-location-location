import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import done from "../test/fixtures/progress-done.json";
import running from "../test/fixtures/progress-running.json";
import { parseProgressFeed } from "../lib/progress";
import { ProgressModal } from "./ProgressModal";

describe("progress modal", () => {
  it("shows the real steps, counts, provider, and cache state while a run works", () => {
    render(<ProgressModal feed={parseProgressFeed(running)} onLoad={vi.fn()} onDismiss={vi.fn()} />);
    const dialog = screen.getByRole("dialog", { name: "Knocking on doors" });
    expect(dialog).toHaveClass("running");
    expect(within(dialog).getByText(/LOCAL RUN \/ RESEARCH \/ my-search/)).toBeInTheDocument();
    expect(within(dialog).getByRole("status")).toHaveTextContent(/2 steps so far/);
    const steps = within(dialog).getByRole("list", { name: "Recorded steps" });
    expect(within(steps).getByText("Drawing the fence")).toBeInTheDocument();
    expect(within(steps).getByText("Overpass returned 17 places inside the boundary")).toBeInTheDocument();
    expect(within(steps).getByText("17 candidates · 68 observations · overpass · cache miss")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: /LOAD THIS RESULT/ })).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "HIDE WHILE IT WORKS" })).toBeInTheDocument();
  });

  it("offers the finished bundle and dismisses", async () => {
    const user = userEvent.setup();
    const onLoad = vi.fn();
    const onDismiss = vi.fn();
    render(<ProgressModal feed={parseProgressFeed(done)} onLoad={onLoad} onDismiss={onDismiss} />);
    const dialog = screen.getByRole("dialog", { name: "Research complete" });
    expect(within(dialog).getByRole("status")).toHaveTextContent(/Finished with 5 recorded steps/);
    expect(within(dialog).getByText("Ranked 17 places; 17 within hard limits, 0 unverified, 0 outside")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /LOAD THIS RESULT/ }));
    expect(onLoad).toHaveBeenCalledWith("runs/my-search/results.json");
    await user.click(within(dialog).getByRole("button", { name: "DISMISS" }));
    expect(onDismiss).toHaveBeenCalled();
  });

  it("says why a run stopped and that the cache is kept", () => {
    const failed = { ...parseProgressFeed(running), status: "failed" as const, error: "provider call cap of 2 would be exceeded" };
    render(<ProgressModal feed={failed} onLoad={vi.fn()} onDismiss={vi.fn()} />);
    const dialog = screen.getByRole("dialog", { name: "Research stopped" });
    expect(within(dialog).getByRole("status")).toHaveTextContent(/provider call cap of 2 would be exceeded/);
    expect(within(dialog).getByRole("status")).toHaveTextContent(/Cache progress is kept/);
    expect(within(dialog).queryByRole("button", { name: /LOAD THIS RESULT/ })).not.toBeInTheDocument();
  });
});
