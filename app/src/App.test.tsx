import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import demoData from "./data/demo-results.json";

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
    expect(screen.getByRole("heading", { name: "Alder Green" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Select map candidate" }));
    expect(screen.getByRole("heading", { name: "Northbridge" })).toBeInTheDocument();
  });

  it("supports arrow-key navigation across candidate buttons", async () => {
    const user = userEvent.setup();
    render(<App />);
    const alder = screen.getByRole("button", { name: /Alder Green/ });
    const northbridge = screen.getByRole("button", { name: /Northbridge/ });
    alder.focus();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(northbridge).toHaveFocus();
    expect(screen.getByRole("heading", { name: "Northbridge" })).toBeInTheDocument();
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
    expect(screen.getByText(/London King's Cross/)).toBeInTheDocument();
    expect(screen.getByText("Station access")).toBeInTheDocument();
    expect(screen.getByText("London last mile")).toBeInTheDocument();
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

  it("reports an incompatible imported schema", async () => {
    const user = userEvent.setup();
    render(<App />);
    const file = new File(['{"schema_version":"2"}'], "old-results.json", { type: "application/json" });
    await user.upload(screen.getByTestId("result-import"), file);
    expect(await screen.findByText(/Incompatible schema 2/)).toBeInTheDocument();
  });
});
