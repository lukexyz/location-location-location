/**
 * The front door: static content that sends a demo visitor to their own local
 * search. Nothing here makes a request; the viewer only renders these strings.
 */

export type Agent = "claude" | "codex";
export type Shell = "powershell" | "posix";

export const REPOSITORY_URL = "https://github.com/lukexyz/location-location-location";
export const WORKFLOW_URL = `${REPOSITORY_URL}/blob/main/skills/location-research/SKILL.md`;
const BOOTSTRAP_BASE = "https://raw.githubusercontent.com/lukexyz/location-location-location/main/scripts";

export const AGENTS: ReadonlyArray<{ id: Agent; label: string; invocation: string }> = [
  { id: "claude", label: "Claude Code", invocation: "/location-research" },
  { id: "codex", label: "Codex", invocation: "$location-research" },
];

export const SHELLS: ReadonlyArray<{ id: Shell; label: string }> = [
  { id: "powershell", label: "Windows PowerShell" },
  { id: "posix", label: "macOS / Linux" },
];

/** One line that clones the repository, installs it, and opens the chosen agent with the skill loaded. */
export function bootstrapCommand(agent: Agent, shell: Shell): string {
  if (shell === "powershell") {
    return `$env:LOCATION3_AGENT = "${agent}"; irm ${BOOTSTRAP_BASE}/bootstrap.ps1 | iex`;
  }
  return `curl -fsSL ${BOOTSTRAP_BASE}/bootstrap.sh | sh -s -- ${agent}`;
}

/** Pick the shell tab that matches the visitor's platform; Windows gets PowerShell, everyone else POSIX. */
export function detectShell(platform: string | undefined): Shell {
  return /win/i.test(platform ?? "") && !/darwin/i.test(platform ?? "") ? "powershell" : "posix";
}

export const NEXT_STEPS: ReadonlyArray<string> = [
  "The repository is cloned into a folder called location-location-location, and its Python and Node dependencies install.",
  "Your agent opens in that folder with the research skill loaded. It asks for an approximate origin, where you need to get to, your housing budget, what matters to you, and which limits are absolute.",
  "Before anything leaves your machine the command prints exactly what will be sent and to whom. Nothing is fetched until you approve it, and there are at most two provider calls per run.",
  "Cited rail, housing, and street-care evidence is gathered by your agent on the subscription you already pay for. Deterministic Python turns it into scores; the agent never assigns one.",
  "This viewer opens on your private result: ranked map, evidence per place, and what-if importance.",
];

export const PRIVACY_NOTES: ReadonlyArray<string> = [
  "Your origin is rounded to about 110 m before it is sent or stored; an exact address is never asked for.",
  "Profiles, destinations, budgets, visit audits, caches, and results stay in gitignored folders on your machine. This viewer never uploads a result.",
  "A free OpenRouteService key upgrades the search boundary to a real drive-time isochrone. Keys live only in your environment and are never written into a bundle.",
];

export const REQUIREMENTS = "Needs git, Python 3.11+, Node 22+, uv, and the agent's own CLI.";
