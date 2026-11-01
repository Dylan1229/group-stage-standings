"""The rank-group task's verdict: eleven named checks on the submitted table, its saved file and the answer key.

Each check is {id, ok, expected, actual, message}. The verdict is valid when all eleven hold, and its
score is the share that hold. Checks that need the answer key are not checked (ok None) without one.
"""

from itertools import pairwise

from . import data
from .checks import (
    canonical,
    echo_problem,
    entry,
    not_checked,
    plain_match,
    plain_row,
    plain_table,
    read_json,
    standings_path,
    verdict,
)
from .pin import reference_problems
from .table import arithmetic_problem, recount, row_differences

MOST = 3  # rows a message names before "+N more"


def listed(problems):
    """Up to MOST problems joined, then how many more."""
    shown = "; ".join(problems[:MOST])
    return shown + (f" (+{len(problems) - MOST} more)" if len(problems) > MOST else "")


def reference_check(problems):
    if problems:
        return entry("reference", False, listed(problems))
    return entry("reference", True, "")


def echo_check(arguments, output):
    problem = echo_problem(output, arguments)
    expected = f"{arguments.tournament} {arguments.group} md{arguments.through_matchday} {arguments.ruleset.value}"
    actual = f"{output.tournament} {output.group} md{output.through_matchday} {output.ruleset.value}"
    message = f"The submission is for another task: {problem}"
    return entry("echo", problem is None, message, expected=expected, actual=actual)


def saved_file(arguments, output, workspace):
    """(the check, the saved JSON or None)."""
    expected = standings_path(arguments)
    if output.path != expected:
        message = f"path is {output.path!r}, expected {expected}: submit the path save_standings returned"
        return entry("saved-file", False, message, expected=expected, actual=output.path), None
    saved, problem = read_json(workspace, expected)
    if problem is None and not isinstance(saved, dict):
        problem = f"{expected} does not hold a JSON object"
    if problem:
        message = f"{problem[0].upper()}{problem[1:]}: call save_standings and submit what it returns"
        return entry("saved-file", False, message, expected=expected, actual=output.path), None
    return entry("saved-file", True, "", expected=expected, actual=output.path), saved


def file_matches(output, saved):
    table = plain_table(output)
    differ = sorted(key for key in set(table) | set(saved) if canonical(table.get(key)) != canonical(saved.get(key)))
    message = f"The saved file differs from the submission in {', '.join(differ)}: submit exactly what save_standings returned"
    return entry("file-matches", not differ, message, expected=[], actual=differ)


def teams_check(found, names):
    if found is None:
        return entry("teams", False, "The task names no bundled group")
    group = data.teams(found)
    problems = [f"{team} is missing" for team in group if team not in names]
    problems += [f"{team} is not a team of the group" for team in sorted(set(names) - set(group))]
    problems += [f"{team} appears {names.count(team)} times" for team in sorted(set(names)) if names.count(team) > 1]
    message = f"The rows must name each of the group's {len(group)} teams once: {listed(problems)}"
    return entry("teams", not problems, message, expected=sorted(group), actual=sorted(names))


def positions_check(rows):
    positions = [row["position"] for row in rows]
    expected = list(range(1, len(rows) + 1))
    ok = bool(rows) and positions == expected
    message = f"Positions are {positions}, expected {expected}" if rows else "The table has no rows"
    return entry("positions", ok, message, expected=expected, actual=positions)


def arithmetic_check(rows):
    problems = [f"{row['team']}: {arithmetic_problem(row)}" for row in rows if arithmetic_problem(row)]
    return entry(
        "arithmetic", not problems, f"A row contradicts itself: {listed(problems)}", expected=[], actual=problems
    )


def stats_check(rows, lines):
    problems = []
    for row in rows:
        if row["team"] not in lines:
            problems.append(f"{row['team']} is not a team of the group")
            continue
        differences = row_differences(row, lines[row["team"]])
        if differences:
            problems.append(f"{row['team']}: {', '.join(differences)}")
    message = f"A row's numbers are not the counted matches': {listed(problems)}"
    return entry("stats", not problems, message, expected=[], actual=problems)


def points_order_check(rows):
    points = [row["points"] for row in rows]
    expected = sorted(points, reverse=True)
    for upper, lower in pairwise(rows):
        if lower["points"] > upper["points"]:
            message = f"{lower['team']} ({lower['points']} pts) is below {upper['team']} ({upper['points']} pts): points rank first"
            return entry("points-order", False, message, expected=expected, actual=points)
    return entry("points-order", True, "", expected=expected, actual=points)


def order_check(names, reference):
    expected = [row.team for row in reference.rows]
    if names == expected:
        return entry("order", True, "", expected=expected, actual=names)
    at = next((index for index, (mine, theirs) in enumerate(zip(names, expected)) if mine != theirs), None)
    if at is None:
        message = f"The table ranks {len(names)} teams, the {reference.ruleset.value} order has {len(expected)}"
    else:
        reason = reference.deciders[min(at, len(reference.deciders) - 1)] if reference.deciders else ""
        message = f"Position {at + 1} is {names[at]}, expected {expected[at]}" + (f" ({reason})" if reason else "")
    return entry("order", False, message, expected=expected, actual=names)


def qualified_check(output, names, reference):
    expected = list(reference.qualified)
    actual = list(output.qualified)
    if actual != expected:
        message = f"qualified is {actual}, expected {expected}"
    elif actual != names[:2]:
        message = f"qualified {actual} is not the first two teams of the submitted rows, {names[:2]}"
    else:
        return entry("qualified", True, "", expected=expected, actual=actual)
    return entry("qualified", False, message, expected=expected, actual=actual)


def verify_task(arguments, output, reference, workspace):
    """``output``: a contract StandingsOutput; ``reference``: the pinned PinnedStandingsOutput, or None."""
    problems = reference_problems(arguments, reference)
    found = data.group(arguments.tournament, arguments.group)
    rows = [plain_row(row) for row in output.rows]
    names = [row["team"] for row in rows]
    file_entry, saved = saved_file(arguments, output, workspace)
    if problems:
        keyed = [not_checked(identifier, "reference") for identifier in ("stats", "order", "qualified")]
    else:
        # The verifier's own count of the answer key's matches, which reference_problems held to the bundled data.
        lines = recount(data.teams(found), [plain_match(match) for match in reference.counted_matches])
        keyed = [stats_check(rows, lines), order_check(names, reference), qualified_check(output, names, reference)]
    entries = [
        reference_check(problems),
        echo_check(arguments, output),
        file_entry,
        file_matches(output, saved) if saved is not None else not_checked("file-matches", "saved-file"),
        teams_check(found, names),
        positions_check(rows),
        arithmetic_check(rows),
        keyed[0],
        points_order_check(rows),
        *keyed[1:],
    ]
    if problems:
        return verdict(entries, "")
    expected = [plain_row(row) for row in reference.rows]
    correct = sum(canonical(mine) == canonical(theirs) for mine, theirs in zip(rows, expected))
    table = ", ".join(f"{row['position']}. {row['team']} {row['points']}" for row in expected)
    success = (
        f"All {len(entries)} checks hold for {arguments.tournament} group {arguments.group} through matchday"
        f" {arguments.through_matchday} under {arguments.ruleset.value}: {table}; {' and '.join(output.qualified)} qualify"
    )
    return verdict(
        entries,
        success,
        rows_correct=f"{correct}/{len(expected)}",
        expected_order=[row["team"] for row in expected],
        deciders=list(reference.deciders),
    )
