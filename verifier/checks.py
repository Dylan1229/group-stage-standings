"""Verdict helpers shared by the verifier modules. Pure functions of their arguments and the files on disk."""

import json
from pathlib import Path

MAX_FILE_BYTES = 1_000_000  # a saved table is about 2 KB
STATS = ("played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points", "fair_play")


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def entry(identifier, ok, message, *, expected=None, actual=None):
    """One named check: ok is True (holds), False (fails) or None (not checked: a check it needs
    failed); message says why it fails or was not checked, "" when it holds."""
    return {
        "id": identifier,
        "ok": ok,
        "expected": expected,
        "actual": actual,
        "message": "" if ok is True else message,
    }


def not_checked(identifier, needs):
    return entry(identifier, None, f"Not checked: {needs} does not hold")


def summary(entries):
    """A failed verdict's message: the first failing check (else the first not checked), then how many more fail."""
    failed = [one for one in entries if one["ok"] is False]
    first = failed[0] if failed else next(one for one in entries if one["ok"] is not True)
    more = f" (+{len(failed) - 1} more failing)" if len(failed) > 1 else ""
    return f"{first['id']}: {first['message']}{more}"


def verdict(entries, success, **details):
    """valid when every check holds; score is the share of checks that hold."""
    held = sum(one["ok"] is True for one in entries)
    valid = held == len(entries)
    return result(valid, success if valid else summary(entries), score=held / len(entries), checks=entries, **details)


def canonical(value):
    """``value`` as one JSON text, so 1, 1.0 and true never compare equal."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=True)


def path_problem(relative):
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts:
        return f"{relative!r} leaves the workspace: a path is relative to it, with no '..'"
    return None


def read_json(workspace, relative):
    """(the JSON in ``relative`` inside ``workspace``, None) or (None, why it cannot be read)."""
    problem = path_problem(relative)
    if problem:
        return None, problem
    try:
        root = Path(workspace).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            return None, f"{relative} leads outside the workspace"
        if not path.is_file():
            return None, f"no file at {relative}"
        if path.stat().st_size > MAX_FILE_BYTES:
            return None, f"{relative} is over {MAX_FILE_BYTES} bytes"
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, RuntimeError):
        return None, f"{relative} cannot be read"
    except (ValueError, RecursionError):
        return None, f"{relative} is not UTF-8 JSON"


def standings_path(value):
    """Where a table for the task input ``value`` is saved, relative to the workspace."""
    return f"standings/{value.tournament}-{value.group}-md{value.through_matchday}-{value.ruleset.value}.json"


def plain_row(row):
    return {
        "position": row.position,
        "team": row.team,
        "played": row.played,
        "won": row.won,
        "drawn": row.drawn,
        "lost": row.lost,
        "goals_for": row.goals_for,
        "goals_against": row.goals_against,
        "goal_difference": row.goal_difference,
        "points": row.points,
        "fair_play": row.fair_play,
    }


def plain_match(match):
    return {
        "id": match.id,
        "md": match.md,
        "status": match.status.value,
        "home": match.home,
        "away": match.away,
        "hg": match.hg,
        "ag": match.ag,
        "hc": list(match.hc),
        "ac": list(match.ac),
    }


def plain_table(value):
    """A SaveInput or StandingsOutput's table as save_standings writes it: every field but path."""
    return {
        "tournament": value.tournament,
        "group": value.group,
        "through_matchday": value.through_matchday,
        "ruleset": value.ruleset.value,
        "rows": [plain_row(row) for row in value.rows],
        "qualified": list(value.qualified),
    }


def echo_problem(value, given):
    """How ``value``'s tournament, group, through_matchday and ruleset differ from ``given``'s, or None."""
    differ = [
        f"{name} {mine!r} (expected {theirs!r})"
        for name, mine, theirs in (
            ("tournament", value.tournament, given.tournament),
            ("group", value.group, given.group),
            ("through_matchday", value.through_matchday, given.through_matchday),
            ("ruleset", value.ruleset.value, given.ruleset.value),
        )
        if mine != theirs
    ]
    return "it names " + ", ".join(differ) if differ else None
