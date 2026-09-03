import { AGENTS, NEXT_STEPS, PRIVACY_NOTES, SHELLS, bootstrapCommand, detectShell } from "./onboarding";

describe("front door commands", () => {
  it("builds one line per agent and shell that names the agent and the bootstrap script", () => {
    expect(bootstrapCommand("claude", "powershell")).toBe(
      '$env:LOCATION3_AGENT = "claude"; irm https://raw.githubusercontent.com/lukexyz/location-location-location/main/scripts/bootstrap.ps1 | iex',
    );
    expect(bootstrapCommand("codex", "posix")).toBe(
      "curl -fsSL https://raw.githubusercontent.com/lukexyz/location-location-location/main/scripts/bootstrap.sh | sh -s -- codex",
    );
    for (const agent of AGENTS) {
      for (const shell of SHELLS) {
        const line = bootstrapCommand(agent.id, shell.id);
        expect(line.split("\n")).toHaveLength(1);
        expect(line).toContain(agent.id);
        expect(line).toContain("https://raw.githubusercontent.com/lukexyz/location-location-location/main/scripts/bootstrap.");
      }
    }
  });

  it("defaults to PowerShell on Windows and POSIX everywhere else", () => {
    expect(detectShell("Win32")).toBe("powershell");
    expect(detectShell("MacIntel")).toBe("posix");
    expect(detectShell("Linux x86_64")).toBe("posix");
    expect(detectShell(undefined)).toBe("posix");
  });

  it("tells the visitor what happens next and what stays private without promising a measurement", () => {
    expect(NEXT_STEPS.some((step) => /agent never assigns one/.test(step))).toBe(true);
    expect(NEXT_STEPS.some((step) => /at most two provider calls/.test(step))).toBe(true);
    expect(PRIVACY_NOTES.some((note) => /never uploads a result/.test(note))).toBe(true);
    expect(PRIVACY_NOTES.some((note) => /110 m/.test(note))).toBe(true);
  });
});
