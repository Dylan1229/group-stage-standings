from __future__ import annotations

import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

from contract import (
    GroupInput,
    GroupMatchesOutput,
    ListTournamentsInput,
    PinnedStandingsOutput,
    Ruleset,
    SaveInput,
    StandingsInput,
    StandingsOutput,
    TournamentsOutput,
)
from plugin import data, get_group_matches, list_tournaments, pin_standings, save_standings
from plugin.data import data_sha256, tournaments

# The bundled data's sha256, as the README records it: a changed dataset fails here first.
DATA_SHA256 = "f3e899518bee264596fea2ddabb2430682b764c7fce5f16283fc393cee0da938"


def test_correct_bundled_data_is_the_documented_file() -> None:
    assert data_sha256() == DATA_SHA256


def test_correct_data_loads_with_unique_seeds_and_a_round_robin_per_group() -> None:
    found = tournaments()
    assert sorted(found) == ["atlantic-cup-2026", "boreal-trophy-2027"]
    sizes = {(tid, letter): len(group.seeds) for tid, t in found.items() for letter, group in t.groups.items()}
    assert sizes == {
        **{("atlantic-cup-2026", letter): 4 for letter in "ABCDEF"},
        ("boreal-trophy-2027", "A"): 5,
        ("boreal-trophy-2027", "B"): 3,
    }
    for tournament in found.values():
        seeds = sorted(seed for group in tournament.groups.values() for seed in group.seeds.values())
        assert seeds == list(range(1, len(seeds) + 1))


def test_correct_list_tournaments_gives_each_group_s_teams_and_last_matchday(tmp_path: Path) -> None:
    listed = list_tournaments(ListTournamentsInput(), tmp_path)
    atlantic, boreal = listed.tournaments
    assert (atlantic.id, atlantic.name, len(atlantic.groups)) == ("atlantic-cup-2026", "Atlantic Cup 2026", 6)
    assert [(g.group, g.last_matchday, g.teams) for g in boreal.groups] == [
        ("A", 5, ["Arvoren", "Belmuth", "Cindral", "Dovask", "Elmora"]),
        ("B", 3, ["Gaventa", "Fyrdal", "Hesperon"]),
    ]
    assert build_output(plain_output(listed), TournamentsOutput) == listed


def test_correct_get_group_matches_shows_every_match_with_postponed_ones_empty(tmp_path: Path) -> None:
    shown = get_group_matches(GroupInput("atlantic-cup-2026", "F"), tmp_path)
    assert [(team.team, team.seed) for team in shown.teams] == [
        ("Ulmera", 6),
        ("Valdessa", 7),
        ("Wexmoor", 13),
        ("Xantha", 19),
    ]
    assert [match.id for match in shown.matches] == ["F1", "F2", "F3", "F4", "F5", "F6"]
    postponed = shown.matches[2]
    assert (postponed.status.value, postponed.hg, postponed.ag, postponed.hc, postponed.ac) == (
        "postponed",
        None,
        None,
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    )
    first = shown.matches[0]
    assert (first.md, first.home, first.away, first.hg, first.ag, first.hc, first.ac) == (
        1,
        "Ulmera",
        "Valdessa",
        2,
        0,
        [1, 0, 0, 0],
        [2, 0, 0, 0],
    )
    assert shown.last_matchday == 3 and "yellow_red" in shown.legend
    assert build_output(plain_output(shown), GroupMatchesOutput) == shown


def test_boundary_get_group_matches_output_stays_compact(tmp_path: Path) -> None:
    """The agent reads it within a 2,048-token reply budget: a few hundred tokens at most."""
    for tournament, group in (("atlantic-cup-2026", "C"), ("boreal-trophy-2027", "A")):
        text = json.dumps(plain_output(get_group_matches(GroupInput(tournament, group), tmp_path)))
        assert len(text) < 2_400


@pytest.mark.parametrize(
    ("tournament", "group", "message"),
    [("nowhere-cup", "A", "unknown tournament"), ("atlantic-cup-2026", "G", "has no group 'G'")],
)
def test_malformed_unknown_tournament_or_group_is_refused(
    tmp_path: Path, tournament: str, group: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        get_group_matches(GroupInput(tournament, group), tmp_path)
    with pytest.raises(ValueError, match=message):
        pin_standings(StandingsInput(tournament, group, 1, Ruleset.FIFA), tmp_path)


@pytest.mark.parametrize(("group", "through"), [("A", 0), ("A", 4), ("A", -1)])
def test_malformed_matchday_out_of_range_is_refused_by_the_answer_key(tmp_path: Path, group: str, through: int) -> None:
    with pytest.raises(ValueError, match="through_matchday must be 1 to 3"):
        pin_standings(StandingsInput("atlantic-cup-2026", group, through, Ruleset.UEFA), tmp_path)


def table(through: int = 3, ruleset: str = "uefa", **changes) -> dict:
    pin = pin_standings(StandingsInput("atlantic-cup-2026", "B", through, Ruleset(ruleset)), Path("."))
    saved = {
        "tournament": "atlantic-cup-2026",
        "group": "B",
        "through_matchday": through,
        "ruleset": ruleset,
        "rows": plain_output(pin)["rows"],
        "qualified": list(pin.qualified),
    }
    return saved | changes


def test_correct_save_standings_writes_the_table_as_given(tmp_path: Path) -> None:
    given = table()
    saved = save_standings(build_output(given, SaveInput), tmp_path)
    assert saved.path == "standings/atlantic-cup-2026-B-md3-uefa.json"
    assert json.loads((tmp_path / saved.path).read_text()) == given
    assert plain_output(saved) == given | {"path": saved.path}
    assert build_output(plain_output(saved), StandingsOutput) == saved


def test_correct_save_standings_replaces_an_earlier_save(tmp_path: Path) -> None:
    first = table()
    save_standings(build_output(first, SaveInput), tmp_path)
    second = table(qualified=["Estoval", "Galdria"])
    saved = save_standings(build_output(second, SaveInput), tmp_path)
    assert json.loads((tmp_path / saved.path).read_text())["qualified"] == ["Estoval", "Galdria"]


def test_correct_save_standings_computes_nothing_so_a_wrong_table_is_saved(tmp_path: Path) -> None:
    wrong = table()
    wrong["rows"][0]["points"] = 99
    saved = save_standings(build_output(wrong, SaveInput), tmp_path)
    assert saved.rows[0].points == 99


def row_change(index: int, **changes) -> dict:
    given = table()
    given["rows"][index] |= changes
    return given


@pytest.mark.parametrize(
    ("given", "message"),
    [
        (table(rows=[]), "1 to 8 rows"),
        (row_change(1, position=3), "positions must be 1, 2, 3"),
        (row_change(1, team="Estoval"), "different team"),
        (row_change(2, team="  "), "different team"),
        (row_change(0, goals_for=-1), "goals_for cannot be negative"),
        (row_change(3, fair_play=2), "fair_play is 0 or negative"),
        (table(qualified=["Estoval"]), "qualified must name two"),
        (table(qualified=["Estoval", "Estoval"]), "qualified must name two"),
        (table(qualified=["Estoval", "Atlantis"]), "qualified must name two"),
        (table(through_matchday=4), "through_matchday must be 1 to 3"),
    ],
)
def test_malformed_save_standings_refuses_a_misshapen_table(tmp_path: Path, given: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        save_standings(build_output(given, SaveInput), tmp_path)
    assert not (tmp_path / "standings").exists()


def test_correct_answer_key_round_trips_through_its_contract_class() -> None:
    pin = pin_standings(StandingsInput("boreal-trophy-2027", "A", 5, Ruleset.FIFA), Path("."))
    assert build_output(plain_output(pin), PinnedStandingsOutput) == pin
    assert pin.data_sha256 == DATA_SHA256


GAME = {"id": "X1", "group": "A", "matchday": 1, "home": "Aldoria", "away": "Brevania", "status": "played"}
NO_CARDS = {"yellow": 0, "second_yellow": 0, "red": 0, "yellow_red": 0}
SEEDS = {"Aldoria": 1, "Brevania": 2, "Corvenna": 3}


@pytest.mark.parametrize(
    ("game", "message"),
    [
        (GAME | {"status": "postponed", "home_goals": 0}, "a postponed match has no goals and no cards"),
        (GAME | {"home_goals": -1, "away_goals": 0, "home_cards": NO_CARDS, "away_cards": NO_CARDS}, "goals must be"),
        (
            GAME | {"home_goals": 1, "away_goals": 0, "home_cards": NO_CARDS | {"red": -1}, "away_cards": NO_CARDS},
            "cards",
        ),
        (GAME | {"away": "Aldoria"}, "two different teams"),
        (GAME | {"away": "Atlantis"}, "two different teams"),
        (GAME | {"matchday": 0}, "matchday must be"),
        (GAME | {"status": "abandoned"}, "status must be"),
    ],
)
def test_malformed_data_is_refused_as_it_loads(game: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        data._game(game, SEEDS)


def test_malformed_group_without_a_full_round_robin_is_refused() -> None:
    raw = {"group": "A", "teams": [{"team": team, "seed": seed} for team, seed in SEEDS.items()]}
    played = {"home_goals": 1, "away_goals": 0, "home_cards": NO_CARDS, "away_cards": NO_CARDS}
    one = GAME | played
    with pytest.raises(ValueError, match="every two teams must meet exactly once"):
        data._group("cup", raw, [one, one | {"id": "X2", "matchday": 2}, one | {"id": "X3", "matchday": 3}])
    twice = [
        one,
        one | {"id": "X2", "away": "Corvenna"},
        one | {"id": "X3", "home": "Brevania", "away": "Corvenna", "matchday": 2},
    ]
    with pytest.raises(ValueError, match="matchday 1 gives a team two matches"):
        data._group("cup", raw, twice)
