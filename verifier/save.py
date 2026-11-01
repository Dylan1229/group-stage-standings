"""save_standings: a table of the right shape for a known group, and a file that holds exactly what it returned."""

from . import data
from .checks import canonical, echo_problem, plain_table, read_json, result, standings_path

MAX_ROWS = 8
COUNTS = ("played", "won", "drawn", "lost", "goals_for", "goals_against", "points")


def shape_problem(value):
    """What is wrong with a SaveInput's table shape, or None. Whether its values are right is verify_task's."""
    if not 1 <= len(value.rows) <= MAX_ROWS:
        return f"rows must hold 1 to {MAX_ROWS} rows, one per team"
    positions = [row.position for row in value.rows]
    if positions != list(range(1, len(value.rows) + 1)):
        return f"positions must be 1, 2, 3, ... down the rows, not {positions}"
    teams = [row.team for row in value.rows]
    if not all(team.strip() for team in teams) or len(set(teams)) != len(teams):
        return "every row must name a different team"
    for row in value.rows:
        counts = {"played": row.played, "won": row.won, "drawn": row.drawn, "lost": row.lost}
        counts |= {"goals_for": row.goals_for, "goals_against": row.goals_against, "points": row.points}
        negative = [name for name in COUNTS if counts[name] < 0]
        if negative:
            return f"{row.team}: {', '.join(negative)} cannot be negative"
        if row.fair_play > 0:
            return f"{row.team}: fair_play is 0 or negative (cards only take points away)"
    qualified = value.qualified
    if len(qualified) != 2 or len(set(qualified)) != 2 or not set(qualified) <= set(teams):
        return "qualified must name two different teams of the rows"
    return None


def verify_input(value):
    problem = data.input_problem(value.tournament, value.group, value.through_matchday) or shape_problem(value)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    problem = echo_problem(output_value, input_value)
    if problem:
        return result(False, f"the saved table is for another task: {problem}")
    table = plain_table(output_value)
    if canonical(table) != canonical(plain_table(input_value)):
        return result(False, "the returned table differs from the table given")
    expected = standings_path(input_value)
    if output_value.path != expected:
        return result(False, f"path is {output_value.path!r}, expected {expected}")
    saved, problem = read_json(workspace, expected)
    if problem:
        return result(False, problem)
    if canonical(saved) != canonical(table):
        return result(False, f"{expected} does not hold the table returned")
    return result(True, f"the table is saved in {expected}", path=expected)
