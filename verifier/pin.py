"""pin_standings, the answer key: its input names a group and matchday, and its table must hold up
against the bundled data counted by the verifier itself (verifier/table.py)."""

from itertools import pairwise

from . import data
from .checks import echo_problem, plain_match, plain_row, result
from .table import recount, row_differences


def verify_input(value):
    problem = data.input_problem(value.tournament, value.group, value.through_matchday)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    problems = reference_problems(input_value, output_value)
    if problems:
        return result(False, problems[0], problems=problems)
    return result(True, "the answer key agrees with the bundled data", data_sha256=output_value.data_sha256)


def reference_problems(arguments, reference):
    """Every way ``reference`` (a PinnedStandingsOutput, or None) is not the answer key of the task
    ``arguments``, checked against the bundled data; [] when it is."""
    if reference is None:
        return ["No reference: pin_standings did not run for this task"]
    problem = data.input_problem(arguments.tournament, arguments.group, arguments.through_matchday)
    if problem:
        return [f"The task cannot be ranked: {problem}"]
    problem = echo_problem(reference, arguments)
    if problem:
        return [f"The reference is for another task: {problem}"]
    if reference.data_sha256 != data.sha256():
        return [
            f"The reference was pinned from other data (sha256 {reference.data_sha256}, the bundled file's is {data.sha256()})"
        ]
    found = data.group(arguments.tournament, arguments.group)
    counted = data.counted(found, arguments.through_matchday)
    if [plain_match(match) for match in reference.counted_matches] != counted:
        return ["The reference's counted matches are not the played matches of matchday 1 to through_matchday"]
    rows = [plain_row(row) for row in reference.rows]
    teams = [row["team"] for row in rows]
    problems = []
    if sorted(teams) != sorted(data.teams(found)):
        problems.append(f"The reference ranks {teams}, not the group's teams {data.teams(found)}")
    if [row["position"] for row in rows] != list(range(1, len(rows) + 1)):
        problems.append("The reference's positions are not 1..n")
    lines = recount(data.teams(found), counted)
    for row in rows:
        differences = row_differences(row, lines[row["team"]]) if row["team"] in lines else ["not in the group"]
        if differences:
            problems.append(f"The reference's {row['team']} row is wrong: {', '.join(differences)}")
    if any(upper["points"] < lower["points"] for upper, lower in pairwise(rows)):
        problems.append("The reference ranks a team above one with more points")
    if list(reference.qualified) != teams[:2]:
        problems.append("The reference's qualified are not its first two teams")
    if len(reference.deciders) != max(len(rows) - 1, 0):
        problems.append("The reference does not explain each pair of neighbouring rows")
    return problems
