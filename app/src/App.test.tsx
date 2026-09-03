import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import demoData from "./data/demo-results.json";
import { Dossier } from "./components/Dossier";
import { parseResultBundle } from "./lib/validateResult";

vi.mock("./components/MapView", () => ({
  MapView: ({ candidates, onSelect }: { candidates: { id: string }[]; onSelect: (id: string) => void }) => (
    <div data-testid="map-view">
      <button type="button" onClick={() => onSelect(candidates[1].id)}>Select map candidate</button>
    </div>
  ),
}));

import App from "./App";

describe("viewer", () => {
  it("keeps map and dossier selection synchronized", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByRole("heading", { name: "Welwyn Garden City" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Select map candidate" }));
    expect(screen.getByRole("heading", { name: "Hemel Hempstead" })).toBeInTheDocument();
  });

  it("supports arrow-key navigation across candidate buttons", async () => {
    const user = userEvent.setup();
    render(<App />);
    const alder = screen.getByRole("button", { name: /Welwyn Garden City/ });
    const hemel = screen.getByRole("button", { name: /Hemel Hempstead/ });
    alder.focus();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(hemel).toHaveFocus();
    expect(screen.getByRole("heading", { name: "Hemel Hempstead" })).toBeInTheDocument();
  });

  it("highlights a favorable raw observation without recoloring its score", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".metric-raw .favorable-observation")).toHaveTextContent(/^0$/);
    expect(container.querySelector(".metric-raw")).toHaveTextContent("0 in 15 min");
    expect(container.querySelector(".metric-raw + .metric-score")).toHaveTextContent("100.0");
  });

  it("shows the full cited rail journey rather than only train time", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Rail intelligence" })).toBeInTheDocument();
    expect(screen.getAllByText(/London King's Cross/).length).toBeGreaterThan(0);
    expect(screen.getByText("Station access")).toBeInTheDocument();
    expect(screen.getByText("London last mile")).toBeInTheDocument();
  });

  it("labels the basis of every fact so a synthetic or estimated value cannot pass as measured", () => {
    render(<App />);
    expect(screen.getAllByText("Basis").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Synthetic").length).toBeGreaterThan(0);
  });

  it("shows route assumptions and score contributions", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Route boundary" })).toBeInTheDocument();
    expect(screen.getByText(/not modelled; fictional boundary/i)).toBeInTheDocument();
    expect(screen.getAllByText(/overall/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Category points").length).toBeGreaterThan(0);
  });

  it("sorts the register with pressed keys without changing authoritative ranks", async () => {
    const user = userEvent.setup();
    render(<App />);
    const sortGroup = screen.getByRole("group", { name: "Sort candidates" });
    const nameKey = within(sortGroup).getByRole("button", { name: "Name" });
    expect(within(sortGroup).getByRole("button", { name: "Rank" })).toHaveAttribute("aria-pressed", "true");
    await user.click(nameKey);
    expect(nameKey).toHaveAttribute("aria-pressed", "true");
    expect(within(sortGroup).getByRole("button", { name: "Rank" })).toHaveAttribute("aria-pressed", "false");
    const candidates = screen.getAllByRole("button", { name: /within limits|limit unverified|outside hard limit/ });
    expect(candidates[0]).toHaveAccessibleName(/Hemel Hempstead/);
    expect(candidates[1]).toHaveAccessibleName(/Maidenhead/);
    expect(candidates[1]).toHaveTextContent("03");
  });

  it("sort keys are keyboard operable", async () => {
    const user = userEvent.setup();
    render(<App />);
    const sortGroup = screen.getByRole("group", { name: "Sort candidates" });
    const confidenceKey = within(sortGroup).getByRole("button", { name: "Confidence" });
    confidenceKey.focus();
    await user.keyboard("{Enter}");
    expect(confidenceKey).toHaveAttribute("aria-pressed", "true");
  });

  it("leads the dossier with instruments, warnings, and limits before cited evidence and readouts", () => {
    const { container } = render(<App />);
    const dossier = container.querySelector(".dossier")!;
    const order = ["score-dial", "instrument-strip", "warning-strip", "constraint-block", "category-block", "rail-block", "housing-block", "street-care-block", "route-context", "readout-block"]
      .map((className) => Array.from(dossier.querySelectorAll("*")).findIndex((element) => element.classList.contains(className)));
    expect(order.every((index) => index >= 0)).toBe(true);
    expect([...order].sort((left, right) => left - right)).toEqual(order);
    expect(within(dossier as HTMLElement).getByRole("img", { name: /Overall suitability 78\.8/ })).toBeInTheDocument();
    expect(screen.getByText("51.803N / 0.208W")).toBeInTheDocument();
    expect(screen.getByText("Coverage")).toBeInTheDocument();
    expect(screen.getByText("Punctuality (time to 3)")).toBeInTheDocument();
  });

  it("counts warnings in an always-visible amber strip that expands to the list", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /Maidenhead/ }));
    const strip = screen.getByText("Evidence warnings").closest("details")!;
    expect(strip).toHaveClass("warning-strip");
    expect(strip).toHaveTextContent("6 warnings");
    expect(strip).not.toHaveAttribute("open");
    await user.click(screen.getByText("Evidence warnings"));
    expect(strip).toHaveAttribute("open");
    expect(screen.getByText(/Purchase comparable sample has fewer than 20 transactions/)).toBeInTheDocument();
  });

  it("shows the limit warning beside an unverified hard limit", () => {
    // The demo bundle has no unverified limit, so the row wording is checked on a modified copy.
    const unverified = structuredClone(demoData);
    unverified.candidates[0].hard_constraints = {
      status: "unknown",
      results: [{
        metric: "door_to_door_commute", operator: "<=", value: 65, actual: null, status: "unknown",
        warning: "No cited journey covers this destination",
      }],
    } as unknown as (typeof demoData)["candidates"][number]["hard_constraints"];
    const { container } = render(<Dossier candidate={parseResultBundle(unverified).candidates[0]} />);
    const dossier = within(container as HTMLElement);
    expect(dossier.getByText("No cited journey covers this destination")).toBeInTheDocument();
    expect(dossier.getByText("no evidence <= 65")).toBeInTheDocument();
    expect(dossier.getByText("UNVERIFIED")).toBeInTheDocument();
  });

  it("labels a distance-proxy envelope as a proxy and shows its assumptions", () => {
    const proxied = structuredClone(demoData);
    proxied.route_boundary = {
      ...proxied.route_boundary,
      type: "distance_proxy",
      provider: "distance-proxy",
      duration_minutes: 30,
      travel_profile: "driving-car",
      traffic_treatment: "not modelled; straight-line distance proxy",
      description: "Distance proxy: 30 min by driving-car approximated as a 14.0 km straight-line radius (40 km/h x 0.7 detour factor); not a routed isochrone. Set ORS_API_KEY for a real one.",
    } as typeof proxied.route_boundary;
    const bundle = parseResultBundle(proxied);
    const { container } = render(<Dossier candidate={bundle.candidates[0]} routeBoundary={bundle.route_boundary} />);
    const route = within(container.querySelector(".route-context") as HTMLElement);
    expect(route.getByText("SEARCH ENVELOPE / distance proxy")).toBeInTheDocument();
    expect(route.getByText("30 min · PROXY")).toBeInTheDocument();
    expect(route.getByText(/14\.0 km straight-line radius/)).toHaveClass("proxy-note");
  });

  it("labels market affordability separately from live listings", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Housing affordability" })).toBeInTheDocument();
    expect(screen.getByText("£390,000")).toBeInTheDocument();
    expect(screen.getByText(/live inventory was not checked/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Search current listings/ })).toBeInTheDocument();
  });

  it("shows a recent visit audit without hiding its proxy evidence", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Street care" })).toBeInTheDocument();
    expect(screen.getByText(/PAVEMENT PRIDE \/ Recent visit audit/i)).toBeInTheDocument();
    expect(screen.getByText("12/1k")).toBeInTheDocument();
    expect(screen.getByText(/Synthetic recent visit audit/)).toBeInTheDocument();
  });

  it("imports valid result JSON locally without a fetch", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const imported = structuredClone(demoData);
    imported.run_id = "private-local-run";
    imported.candidates[0].name = "Test Reach";
    render(<App />);
    const file = new File([JSON.stringify(imported)], "private-results.json", { type: "application/json" });
    await user.upload(screen.getByTestId("result-import"), file);
    expect(await screen.findByText("private-results.json loaded in this tab only")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Test Reach" })).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("reports an incompatible imported schema without offering to reset a demo that is still active", async () => {
    const user = userEvent.setup();
    render(<App />);
    const file = new File(['{"schema_version":"1"}'], "old-results.json", { type: "application/json" });
    await user.upload(screen.getByTestId("result-import"), file);
    expect(await screen.findByText(/Incompatible schema 1.*rerun the research command/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reset demo" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Welwyn Garden City" })).toBeInTheDocument();
  });

  it("rejects an oversized file with both the size and candidate limits named", async () => {
    const user = userEvent.setup();
    render(<App />);
    const big = new File([new Uint8Array(1024)], "huge-results.json", { type: "application/json" });
    Object.defineProperty(big, "size", { value: 25 * 1024 * 1024 + 1 });
    await user.upload(screen.getByTestId("result-import"), big);
    const status = await screen.findByText(/25 MB local import limit/);
    expect(status).toHaveTextContent(/1,000 candidates/);
  });

  it("resets the sort mode to rank on import and on reset", async () => {
    const user = userEvent.setup();
    render(<App />);
    const sortGroup = () => screen.getByRole("group", { name: "Sort candidates" });
    await user.click(within(sortGroup()).getByRole("button", { name: "Name" }));
    expect(within(sortGroup()).getByRole("button", { name: "Name" })).toHaveAttribute("aria-pressed", "true");
    const file = new File([JSON.stringify(demoData)], "again.json", { type: "application/json" });
    await user.upload(screen.getByTestId("result-import"), file);
    expect(await screen.findByText("again.json loaded in this tab only")).toBeInTheDocument();
    expect(within(sortGroup()).getByRole("button", { name: "Rank" })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(sortGroup()).getByRole("button", { name: "Name" }));
    await user.click(screen.getByRole("button", { name: "Reset demo" }));
    expect(within(sortGroup()).getByRole("button", { name: "Rank" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("button", { name: "Reset demo" })).not.toBeInTheDocument();
  });

  it("offers the front door only while the sample is active", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByRole("button", { name: /RUN YOUR OWN SEARCH/ })).toBeInTheDocument();
    expect(screen.getByText(/REAL TOWNS, SYNTHETIC EVIDENCE/)).toBeInTheDocument();
    const file = new File([JSON.stringify(demoData)], "mine.json", { type: "application/json" });
    await user.upload(screen.getByTestId("result-import"), file);
    expect(await screen.findByText("mine.json loaded in this tab only")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /RUN YOUR OWN SEARCH/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reset demo" }));
    expect(screen.getByRole("button", { name: /RUN YOUR OWN SEARCH/ })).toBeInTheDocument();
  });

  it("opens a modal with one copyable line per agent and shell, and never fetches", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("fetch", fetchSpy);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<App />);
    await user.click(screen.getByRole("button", { name: /RUN YOUR OWN SEARCH/ }));
    const dialog = screen.getByRole("dialog", { name: "Run your own search" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("heading", { name: "Run your own search" })).toHaveFocus();
    expect(within(dialog).getByRole("tab", { name: "Claude Code" })).toHaveAttribute("aria-selected", "true");
    const command = () => screen.getByTestId("bootstrap-command").textContent ?? "";
    expect(command()).toMatch(/bootstrap\.(ps1|sh)/);
    expect(command()).toContain("claude");
    await user.click(within(dialog).getByRole("button", { name: "macOS / Linux" }));
    expect(command()).toMatch(/^curl -fsSL .*bootstrap\.sh \| sh -s -- claude$/);
    await user.click(within(dialog).getByRole("tab", { name: "Codex" }));
    expect(command()).toMatch(/sh -s -- codex$/);
    expect(within(dialog).getByText("$location-research")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Windows PowerShell" }));
    expect(command()).toMatch(/^\$env:LOCATION3_AGENT = "codex"; irm .*bootstrap\.ps1 \| iex$/);
    await user.click(within(dialog).getByRole("button", { name: "Copy the command" }));
    expect(writeText).toHaveBeenCalledWith(command());
    expect(await within(dialog).findByText("Copied to the clipboard")).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { name: "What happens next" })).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { name: "What stays private" })).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: /full research workflow/ })).toHaveAttribute("href", expect.stringContaining("SKILL.md"));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("keeps the load-state disclosure in the document at every width", () => {
    const { container } = render(<App />);
    const status = container.querySelector(".load-state")!;
    expect(status).toHaveAttribute("role", "status");
    expect(status).toHaveTextContent("Sample data: real towns, synthetic evidence");
    expect(status).not.toHaveClass("visually-hidden");
  });

  it("tunes importance as a labelled what-if without changing researched ranks", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByText("RESEARCHED WEIGHTS")).toBeInTheDocument();
    const commute = screen.getByLabelText(/Door-to-door commute/);
    fireEvent.change(commute, { target: { value: "0" } });
    const cafes = screen.getByLabelText(/Cafés/);
    fireEvent.change(cafes, { target: { value: "5" } });
    expect(screen.getByText("WHAT-IF ACTIVE")).toBeInTheDocument();
    // The status rail and the dossier both announce the preview.
    expect(screen.getAllByText(/What-if preview/i).length).toBeGreaterThanOrEqual(2);
    const entries = screen.getAllByRole("button", { name: /within limits|limit unverified|outside hard limit/ });
    expect(entries.map((entry) => entry.querySelector(".rank-number")!.textContent).sort()).toEqual(["01", "02", "03"]);
    expect(entries[0]).toHaveTextContent(/researched/);
    await user.click(screen.getByRole("button", { name: "Restore researched importance" }));
    expect(screen.getByText("RESEARCHED WEIGHTS")).toBeInTheDocument();
    expect(screen.queryAllByText(/What-if preview/i)).toHaveLength(0);
  });

  it("tunes category importance above its metrics and restores both with one button", async () => {
    const user = userEvent.setup();
    render(<App />);
    const group = screen.getByRole("group", { name: "Core fit importance" });
    const category = within(group).getByLabelText(/Core fit/);
    expect(within(group).getByText(/Category · researched 5/)).toBeInTheDocument();
    const rows = Array.from(group.querySelectorAll("input[type=range]"));
    expect(rows[0]).toBe(category);
    expect(rows.length).toBe(3);
    fireEvent.change(category, { target: { value: "0" } });
    expect(screen.getByText("WHAT-IF ACTIVE")).toBeInTheDocument();
    expect(screen.getByLabelText("What-if preview")).toHaveTextContent(/covering 100% of the intended category weight/);
    const whatIfScores = screen.getAllByText(/^\d+\.\d$/, { selector: ".rank-score.whatif" });
    expect(whatIfScores.length).toBe(3);
    await user.click(screen.getByRole("button", { name: "Restore researched importance" }));
    expect(screen.getByText("RESEARCHED WEIGHTS")).toBeInTheDocument();
    expect(category).toHaveValue("5");
  });

  it("shows no evidence rather than full confidence when every weight is zero", () => {
    const { container } = render(<App />);
    for (const slider of screen.getAllByRole("slider")) {
      fireEvent.change(slider, { target: { value: "0" } });
    }
    expect(screen.getByText("WHAT-IF ACTIVE")).toBeInTheDocument();
    const preview = screen.getByLabelText("What-if preview");
    expect(preview).toHaveTextContent("confidence —");
    expect(preview).toHaveTextContent("no evidence weighted");
    expect(preview).not.toHaveTextContent(/confidence 100%/);
    expect(container.querySelector(".instrument-strip .readout.preview strong")).toHaveTextContent("0.0 · —");
  });
});
