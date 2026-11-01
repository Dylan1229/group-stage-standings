"""The bundled tournaments as the verifier reads them, independently of src/: the file itself, read
from the plugin folder, and the views the tools must give of it."""

import hashlib
import json
from functools import cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "src" / "plugin" / "data" / "tournaments.json"
CARDS = ("yellow", "second_yellow", "red", "yellow_red")


@cache
def raw_bytes():
    return DATA.read_bytes()


def sha256():
    return hashlib.sha256(raw_bytes()).hexdigest()


@cache
def tournaments():
    """tournament id -> {"name", "groups": {letter: {"teams": [(team, seed)] best seed first, "matches": [...]}}}."""
    found = {}
    for tournament in json.loads(raw_bytes().decode("utf-8"))["tournaments"]:
        groups = {}
        for group in tournament["groups"]:
            teams = sorted(((team["team"], team["seed"]) for team in group["teams"]), key=lambda pair: pair[1])
            matches = [view(match) for match in tournament["matches"] if match["group"] == group["group"]]
            groups[group["group"]] = {"teams": teams, "matches": sorted(matches, key=lambda match: match["md"])}
        found[tournament["id"]] = {"name": tournament["name"], "groups": groups}
    return found


def view(match):
    """A match as get_group_matches must show it."""
    played = match["status"] == "played"
    return {
        "id": match["id"],
        "md": match["matchday"],
        "status": match["status"],
        "home": match["home"],
        "away": match["away"],
        "hg": match["home_goals"] if played else None,
        "ag": match["away_goals"] if played else None,
        "hc": [match["home_cards"][kind] for kind in CARDS] if played else [0, 0, 0, 0],
        "ac": [match["away_cards"][kind] for kind in CARDS] if played else [0, 0, 0, 0],
    }


def group(tournament, letter):
    """The group's teams and matches, or None when the tournament or group is unknown."""
    found = tournaments().get(tournament)
    return None if found is None else found["groups"].get(letter)


def last_matchday(found):
    return max(match["md"] for match in found["matches"])


def teams(found):
    return [team for team, _seed in found["teams"]]


def counted(found, through_matchday):
    """The matches a table through ``through_matchday`` counts: played, of matchday 1 to it."""
    return [match for match in found["matches"] if match["status"] == "played" and match["md"] <= through_matchday]


def input_problem(tournament, letter, through_matchday=None):
    """Why a tournament, group (and through_matchday) cannot be ranked, or None."""
    known = tournaments()
    if tournament not in known:
        return f"unknown tournament {tournament!r}: one of {', '.join(sorted(known))}"
    found = group(tournament, letter)
    if found is None:
        return f"{tournament} has no group {letter!r}: groups {', '.join(sorted(known[tournament]['groups']))}"
    last = last_matchday(found)
    if through_matchday is not None and not 1 <= through_matchday <= last:
        return f"through_matchday must be 1 to {last} for {tournament} group {letter}, not {through_matchday}"
    return None
