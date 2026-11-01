"""The answer key against tables worked out by hand from tournaments.json, not by any code path.

Each golden row is (team, played, won, drawn, lost, goals_for, goals_against, points, fair_play),
in rank order; the comment over each table says which criterion decides its ties.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from contract import Ruleset, StandingsInput
from plugin import pin_standings

ATLANTIC = "atlantic-cup-2026"
BOREAL = "boreal-trophy-2027"

GROUP_A_MD3 = [
    ("Aldoria", 3, 3, 0, 0, 9, 2, 9, -1),
    ("Brevania", 3, 2, 0, 1, 4, 3, 6, -3),
    ("Corvenna", 3, 1, 0, 2, 3, 5, 3, -3),
    ("Dalmira", 3, 0, 0, 3, 1, 7, 0, -12),
]
# Fenlark and Galdria on 4 points: Galdria's goal difference (+3 v 0), Fenlark's 1-0 head-to-head win.
ESTOVAL = ("Estoval", 3, 2, 1, 0, 5, 2, 7, -2)
GALDRIA = ("Galdria", 3, 1, 1, 1, 6, 3, 4, -4)
FENLARK = ("Fenlark", 3, 1, 1, 1, 1, 1, 4, -5)
HARVOLT = ("Harvolt", 3, 0, 1, 2, 0, 6, 1, -7)
# Jorvale, Kelmora and Istrena all on 6 points, +1, 3 goals; among the three, Istrena scored 1 and the
# others 2 (each 3 points, goal difference 0). fifa: Jorvale and Kelmora stay level, fair play -2 v -3.
# uefa: head to head again between Jorvale and Kelmora only: Kelmora won 2-1.
JORVALE = ("Jorvale", 3, 2, 0, 1, 3, 2, 6, -2)
KELMORA = ("Kelmora", 3, 2, 0, 1, 3, 2, 6, -3)
ISTRENA = ("Istrena", 3, 2, 0, 1, 3, 2, 6, -6)
LUNESSA = ("Lunessa", 3, 0, 0, 3, 1, 4, 0, -8)
# Matchday 1: Jorvale and Istrena both won 1-0 and have not met: fair play -1 v -2. Kelmora and Lunessa
# both lost 0-1 with one yellow each: seed 16 v 22.
GROUP_C_MD1 = [
    ("Jorvale", 1, 1, 0, 0, 1, 0, 3, -1),
    ("Istrena", 1, 1, 0, 0, 1, 0, 3, -2),
    ("Kelmora", 1, 0, 0, 1, 0, 1, 0, -1),
    ("Lunessa", 1, 0, 0, 1, 0, 1, 0, -1),
]
# Matchday 2: Kelmora and Jorvale level on 3 points, 0 and 2 goals; fifa's head to head (4): Kelmora won 2-1.
GROUP_C_MD2 = [
    ("Istrena", 2, 2, 0, 0, 3, 1, 6, -3),
    ("Kelmora", 2, 1, 0, 1, 2, 2, 3, -2),
    ("Jorvale", 2, 1, 0, 1, 2, 2, 3, -1),
    ("Lunessa", 2, 0, 0, 2, 1, 3, 0, -3),
]
# Norvik and Marovia: 4 points, 3-2 each, a 1-1 draw between them. Fair play -3 (three yellows) v -5
# (a yellow and a red: fewer cards, more points lost).
GROUP_D_MD3 = [
    ("Ostrenna", 3, 2, 1, 0, 2, 0, 7, -2),
    ("Norvik", 3, 1, 1, 1, 3, 2, 4, -3),
    ("Marovia", 3, 1, 1, 1, 3, 2, 4, -5),
    ("Pellucia", 3, 0, 1, 2, 0, 4, 1, -6),
]
# Matchday 1: all four on 1 point. Marovia and Norvik (1-1) on goals scored over Ostrenna and Pellucia
# (0-0); then fair play inside each pair: 0 v -1, -1 v -2.
GROUP_D_MD1 = [
    ("Marovia", 1, 0, 1, 0, 1, 1, 1, 0),
    ("Norvik", 1, 0, 1, 0, 1, 1, 1, -1),
    ("Ostrenna", 1, 0, 1, 0, 0, 0, 1, -1),
    ("Pellucia", 1, 0, 1, 0, 0, 0, 1, -2),
]
# Sorvane and Rivelle: 4 points, 4-4, drew 2-2, fair play -3 each (one second yellow v three yellows):
# seed 12 v 18, though Rivelle comes first alphabetically.
GROUP_E_MD3 = [
    ("Quenra", 3, 2, 1, 0, 4, 2, 7, -3),
    ("Sorvane", 3, 1, 1, 1, 4, 4, 4, -3),
    ("Rivelle", 3, 1, 1, 1, 4, 4, 4, -3),
    ("Tamberg", 3, 0, 1, 2, 0, 2, 1, -7),
]
# Ulmera v Wexmoor was postponed: both have played 2.
GROUP_F_MD3 = [
    ("Ulmera", 2, 1, 1, 0, 3, 1, 4, -2),
    ("Valdessa", 3, 1, 1, 1, 3, 4, 4, -3),
    ("Wexmoor", 2, 0, 2, 0, 3, 3, 2, -4),
    ("Xantha", 3, 0, 2, 1, 2, 3, 2, -4),
]
# Five teams: Cindral and Belmuth on 7 points and +1; fifa: goals scored 5 v 2; uefa: Belmuth won 1-0.
ARVOREN = ("Arvoren", 4, 3, 1, 0, 8, 3, 10, -2)
CINDRAL = ("Cindral", 4, 2, 1, 1, 5, 4, 7, -3)
BELMUTH = ("Belmuth", 4, 2, 1, 1, 2, 1, 7, -4)
DOVASK = ("Dovask", 4, 1, 0, 3, 3, 6, 3, -9)
ELMORA = ("Elmora", 4, 0, 1, 3, 1, 5, 1, -7)
# Matchday 1: Arvoren has played nothing yet; Belmuth and Elmora drew 0-0 with a yellow each: seed 4 v 8.
BOREAL_A_MD1 = [
    ("Cindral", 1, 1, 0, 0, 2, 1, 3, 0),
    ("Belmuth", 1, 0, 1, 0, 0, 0, 1, -1),
    ("Elmora", 1, 0, 1, 0, 0, 0, 1, -1),
    ("Arvoren", 0, 0, 0, 0, 0, 0, 0, 0),
    ("Dovask", 1, 0, 0, 1, 1, 2, 0, -2),
]
# Three teams, three 1-1 draws: fair play -1 for Hesperon, then Gaventa and Fyrdal on -2: seed 2 v 3.
BOREAL_B_MD3 = [
    ("Hesperon", 2, 0, 2, 0, 2, 2, 2, -1),
    ("Gaventa", 2, 0, 2, 0, 2, 2, 2, -2),
    ("Fyrdal", 2, 0, 2, 0, 2, 2, 2, -2),
]

GOLDEN = [
    (ATLANTIC, "A", 3, "fifa", GROUP_A_MD3),
    (ATLANTIC, "A", 3, "uefa", GROUP_A_MD3),
    (ATLANTIC, "B", 3, "fifa", [ESTOVAL, GALDRIA, FENLARK, HARVOLT]),
    (ATLANTIC, "B", 3, "uefa", [ESTOVAL, FENLARK, GALDRIA, HARVOLT]),
    (ATLANTIC, "C", 3, "fifa", [JORVALE, KELMORA, ISTRENA, LUNESSA]),
    (ATLANTIC, "C", 3, "uefa", [KELMORA, JORVALE, ISTRENA, LUNESSA]),
    (ATLANTIC, "C", 1, "fifa", GROUP_C_MD1),
    (ATLANTIC, "C", 1, "uefa", GROUP_C_MD1),
    (ATLANTIC, "C", 2, "fifa", GROUP_C_MD2),
    (ATLANTIC, "C", 2, "uefa", GROUP_C_MD2),
    (ATLANTIC, "D", 3, "fifa", GROUP_D_MD3),
    (ATLANTIC, "D", 3, "uefa", GROUP_D_MD3),
    (ATLANTIC, "D", 1, "fifa", GROUP_D_MD1),
    (ATLANTIC, "D", 1, "uefa", GROUP_D_MD1),
    (ATLANTIC, "E", 3, "fifa", GROUP_E_MD3),
    (ATLANTIC, "E", 3, "uefa", GROUP_E_MD3),
    (ATLANTIC, "F", 3, "fifa", GROUP_F_MD3),
    (ATLANTIC, "F", 3, "uefa", GROUP_F_MD3),
    (BOREAL, "A", 5, "fifa", [ARVOREN, CINDRAL, BELMUTH, DOVASK, ELMORA]),
    (BOREAL, "A", 5, "uefa", [ARVOREN, BELMUTH, CINDRAL, DOVASK, ELMORA]),
    (BOREAL, "A", 1, "fifa", BOREAL_A_MD1),
    (BOREAL, "A", 1, "uefa", BOREAL_A_MD1),
    (BOREAL, "B", 3, "fifa", BOREAL_B_MD3),
    (BOREAL, "B", 3, "uefa", BOREAL_B_MD3),
]


def pinned(tournament: str, group: str, through: int, ruleset: str):
    return pin_standings(StandingsInput(tournament, group, through, Ruleset(ruleset)), Path("."))


def golden_rows(table: list[tuple]) -> list[tuple]:
    """Each golden row with its position and goal difference, in the order rows list their fields."""
    return [
        (position, team, played, won, drawn, lost, gf, ga, gf - ga, points, fair_play)
        for position, (team, played, won, drawn, lost, gf, ga, points, fair_play) in enumerate(table, 1)
    ]


@pytest.mark.parametrize(("tournament", "group", "through", "ruleset", "table"), GOLDEN)
def test_correct_answer_key_matches_the_hand_worked_table(
    tournament: str, group: str, through: int, ruleset: str, table: list[tuple]
) -> None:
    pin = pinned(tournament, group, through, ruleset)
    rows = [
        (
            r.position,
            r.team,
            r.played,
            r.won,
            r.drawn,
            r.lost,
            r.goals_for,
            r.goals_against,
            r.goal_difference,
            r.points,
            r.fair_play,
        )
        for r in pin.rows
    ]
    assert rows == golden_rows(table)
    assert pin.qualified == [table[0][0], table[1][0]]


def test_boundary_the_rulesets_disagree_on_two_teams_level_on_points() -> None:
    fifa, uefa = pinned(ATLANTIC, "B", 3, "fifa"), pinned(ATLANTIC, "B", 3, "uefa")
    assert fifa.qualified == ["Estoval", "Galdria"] and uefa.qualified == ["Estoval", "Fenlark"]
    assert fifa.deciders[1] == "Galdria over Fenlark by fifa (2) goal difference: 3 v 0"
    assert uefa.deciders[1] == "Fenlark over Galdria by uefa (2) head-to-head points among Fenlark, Galdria: 3 v 0"


def test_boundary_uefa_reapplies_head_to_head_and_fifa_does_not() -> None:
    fifa, uefa = pinned(ATLANTIC, "C", 3, "fifa"), pinned(ATLANTIC, "C", 3, "uefa")
    assert fifa.deciders[:2] == [
        "Jorvale over Kelmora by fifa (7) fair play: -2 v -3",
        "Kelmora over Istrena by fifa (6) head-to-head goals scored among Istrena, Jorvale, Kelmora: 2 v 1",
    ]
    assert uefa.deciders[:2] == [
        "Kelmora over Jorvale by uefa (5) reapplied head-to-head points among Jorvale, Kelmora: 3 v 0",
        "Jorvale over Istrena by uefa (4) head-to-head goals scored among Istrena, Jorvale, Kelmora: 2 v 1",
    ]


def test_boundary_fair_play_then_seed_decide_full_identities() -> None:
    assert pinned(ATLANTIC, "D", 3, "uefa").deciders[1] == "Norvik over Marovia by uefa (8) fair play: -3 v -5"
    assert pinned(ATLANTIC, "E", 3, "fifa").deciders[1] == "Sorvane over Rivelle by fifa (8) lower seed: 12 v 18"
    assert pinned(BOREAL, "B", 3, "uefa").deciders == [
        "Hesperon over Gaventa by uefa (8) fair play: -1 v -2",
        "Gaventa over Fyrdal by uefa (9) lower seed: 2 v 3",
    ]


def test_boundary_postponed_match_is_never_counted() -> None:
    pin = pinned(ATLANTIC, "F", 3, "fifa")
    assert "F3" not in [match.id for match in pin.counted_matches]
    assert [row.played for row in pin.rows] == [2, 3, 2, 3]


def test_boundary_through_matchday_counts_only_matchdays_up_to_it() -> None:
    pin = pinned(BOREAL, "A", 2, "uefa")
    assert [match.id for match in pin.counted_matches] == ["A1", "A2", "A3", "A4"]
    assert all(match.md <= 2 for match in pin.counted_matches)


def test_correct_every_table_explains_each_neighbouring_pair_in_the_upper_team_s_favour() -> None:
    for tournament, group, through, ruleset, _ in GOLDEN:
        pin = pinned(tournament, group, through, ruleset)
        assert len(pin.deciders) == len(pin.rows) - 1
        for upper, lower, decider in zip(pin.rows, pin.rows[1:], pin.deciders):
            assert decider.startswith(f"{upper.team} over {lower.team} by {ruleset} (")
            mine, theirs = (int(value) for value in decider.rsplit(": ", 1)[1].split(" v "))
            assert mine < theirs if "seed" in decider else mine > theirs
