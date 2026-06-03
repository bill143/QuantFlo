#!/usr/bin/env python
"""Boot the QUANTFLO swarm.

Registers all ten team agents, runs the boot lifecycle, prints each team's role
and status, verifies every agent's status round-trips through the state bus, then
exits cleanly. Contains no trading logic.

The state-bus backend is selectable: ``--bus memory`` (default, in-memory) or
``--bus redis`` (the Phase 1 Redis-backed bus). Either way the same ten teams boot
and register against the same StateBus interface.

It also performs a best-effort, non-fatal probe for the vendored ruflo runtime and
reports whether it is available. The probe never affects the exit code, so this
entrypoint and CI run without Node.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quantflo.core.state_bus import StateBus, create_state_bus
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


def main(state_bus: StateBus | None = None) -> int:
    """Boot the swarm on ``state_bus`` (default in-memory) and return an exit code."""
    swarm = build_default_swarm(state_bus=state_bus)
    swarm.boot()

    agents = sorted(swarm.agents, key=lambda a: a.team_no)
    print(LINE)
    print("QUANTFLO swarm boot")
    print(LINE)
    for agent in agents:
        print(f"  Team {agent.team_no:>2}  {agent.name}  [{agent.status.value}]  ({agent.key})")
        print(f"          role: {agent.role}")
    print("-" * 78)

    verified = sum(
        1
        for agent in agents
        if swarm.state_bus.get_state("orchestration", f"agent:{agent.key}") == agent.status.value
    )
    print(f"Registered agents : {len(agents)}")
    print(f"State bus         : {type(swarm.state_bus).__name__} "
          f"({verified}/{len(agents)} agent states verified)")
    print(f"Backbone          : {probe_ruflo()}")

    not_ready = [a.key for a in agents if a.status is not AgentStatus.READY]
    if len(agents) != EXPECTED_TEAMS:
        print(f"ERROR: expected {EXPECTED_TEAMS} teams, registered {len(agents)}", file=sys.stderr)
        return 1
    if not_ready:
        print(f"ERROR: teams not READY: {', '.join(not_ready)}", file=sys.stderr)
        return 1
    if verified != len(agents):
        print("ERROR: state bus did not round-trip all agent states", file=sys.stderr)
        return 1

    print(f"Swarm boot OK - all {EXPECTED_TEAMS} teams READY, bus verified. Exiting cleanly.")
    return 0


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Boot the QUANTFLO swarm")
    parser.add_argument(
        "--bus",
        choices=("memory", "redis"),
        default="memory",
        help="state-bus backend (default: memory)",
    )
    args = parser.parse_args()
    return main(state_bus=create_state_bus(args.bus))


if __name__ == "__main__":
    raise SystemExit(_cli())
