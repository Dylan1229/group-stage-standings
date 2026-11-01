"""save_standings: writes the agent's table to the workspace as it is given. It checks the table's
shape (positions, names, signs) and computes nothing: whether the table is right is the verifier's."""

from __future__ import annotations

import json
from pathlib import Path

from slimconfig import plain_output

from contract import SaveInput, StandingsOutput
from plugin.data import check_matchday, find_group

FOLDER = "standings"
MAX_ROWS = 8
COUNTS = ("played", "won", "drawn", "lost", "goals_for", "goals_against", "points")


def standings_path(tournament: str, group: str, through_matchday: int, ruleset: str) -> str:
    """Where a table is saved, relative to the workspace."""
    return f"{FOLDER}/{tournament}-{group}-md{through_matchday}-{ruleset}.json"


def shape_problem(given: SaveInput) -> str | None:
    """What is wrong with the table's shape, or None. Nothing here judges a value right or wrong."""
    if not 1 <= len(given.rows) <= MAX_ROWS:
        return f"rows must hold 1 to {MAX_ROWS} rows, one per team"
    positions = [row.position for row in given.rows]
    if positions != list(range(1, len(given.rows) + 1)):
        return f"positions must be 1, 2, 3, ... down the rows, not {positions}"
    teams = [row.team for row in given.rows]
    if not all(team.strip() for team in teams) or len(set(teams)) != len(teams):
        return "every row must name a different team"
    for row in given.rows:
        negative = [name for name in COUNTS if getattr(row, name) < 0]
        if negative:
            return f"{row.team}: {', '.join(negative)} cannot be negative"
        if row.fair_play > 0:
            return f"{row.team}: fair_play is 0 or negative (cards only take points away)"
    if len(given.qualified) != 2 or len(set(given.qualified)) != 2 or not set(given.qualified) <= set(teams):
        return "qualified must name two different teams of the rows"
    return None


def save_standings(given: SaveInput, workspace: Path) -> StandingsOutput:
    """Write the table to standings/<tournament>-<group>-md<N>-<ruleset>.json, replacing an earlier save."""
    check_matchday(find_group(given.tournament, given.group), given.through_matchday)
    problem = shape_problem(given)
    if problem:
        raise ValueError(problem)
    relative = standings_path(given.tournament, given.group, given.through_matchday, given.ruleset.value)
    root = workspace.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("the standings file must stay inside the plugin workspace")
    path.parent.mkdir(parents=True, exist_ok=True)
    saved = plain_output(given)
    path.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
    return StandingsOutput(**{name: getattr(given, name) for name in saved}, path=relative)
