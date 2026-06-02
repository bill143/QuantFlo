#!/usr/bin/env python
"""Boot the QUANTFLO swarm.

Registers all ten team agents, runs the boot lifecycle, prints each team's role
and status, then exits cleanly. Phase 0 entrypoint — contains no trading logic.

It also performs a best-effort, non-fatal probe for the vendored ruflo runtime
(the TypeScript orchestration backbone) and reports whether it is available. The
probe never affects the exit code, so this entrypoint and CI run without Node.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from quantflo.orchestration import AgentStatus, build_default_swarm

EXPECTED_TEAMS = 10
LINE = "=" * 78
REPO_ROOT = Path(__file__).resolve().parent.parent


def probe_ruflo() -> str:
    """Detect the vendored ruflo runtime by inspecting the pinned install.

    Filesystem-only and side-effect free: it does NOT execute the ruflo CLI,
    which eagerly loads an embedding model on startup. The live runtime bridge
    is a Phase 1 concern; Phase 0 only confirms the backbone is vendored.
    """
    pkg = REPO_ROOT / "node_modules" / "ruflo" / "package.json"
    if not pkg.is_file():
        return "ruflo runtime: not vendored - run `npm install` - Phase 1 bridge pending"
    try:
        version = json.loads(pkg.read_text(encoding="utf-8")).get("version", "unknown")
    except (OSError, ValueError):
        return "ruflo runtime: vendored (version unreadable) - Phase 1 bridge pending"
    return f"ruflo runtime: vendored (v{version}) - Phase 1 bridge pending"


def main() -> int:
    """Boot the swarm and return a process exit code."""
    swarm = build_default_swarm()
    swarm.boot()

    agents = sorted(swarm.agents, key=lambda a: a.team_no)
    print(LINE)
    print("QUANTFLO swarm boot - Phase 0 foundation")
    print(LINE)
    for agent in agents:
        print(
            f"  Team {agent.team_no:>2}  {agent.key:<16}  "
            f"[{agent.status.value:<5}]  {agent.role}"
        )
    print("-" * 78)
    print(f"Registered agents : {len(agents)}")
    print(f"Backbone          : {probe_ruflo()}")

    not_ready = [a.key for a in agents if a.status is not AgentStatus.READY]
    if len(agents) != EXPECTED_TEAMS:
        print(f"ERROR: expected {EXPECTED_TEAMS} teams, registered {len(agents)}", file=sys.stderr)
        return 1
    if not_ready:
        print(f"ERROR: teams not READY: {', '.join(not_ready)}", file=sys.stderr)
        return 1

    print("Swarm boot OK - all 10 teams READY. Exiting cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
