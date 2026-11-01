"""pin_standings, the answer key: a group's table under the fifa or uefa tiebreakers, computed plainly.

Only played matches of matchday 1 to ``through_matchday`` count. A win is worth 3 points, a draw 1.
A team's fair-play points are -1 per yellow, -3 per second_yellow, -4 per red and -5 per yellow_red
(higher is better). Every criterion ranks the higher value first, but the seed, where 1 is best.

fifa: (1) points, (2) goal difference, (3) goals scored, in all counted matches; a set of teams
still level on all three is ranked once, over the matches among that whole set, by (4) points,
(5) goal difference, (6) goals scored; then (7) fair-play points in all counted matches; (8) seed.

uefa: (1) points; a set level on points is ranked by (2) points, (3) goal difference, (4) goals
scored in the matches among them; (5) when that separates some of them but leaves two or more
level, (2)-(4) apply again to the matches among only those, and so on; a set that (2)-(4) cannot
split at all is ranked by (6) goal difference, (7) goals scored in all counted matches, (8)
fair-play points, (9) seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby, pairwise
from pathlib import Path

from contract import PinnedStandingsOutput, Row, Ruleset, StandingsInput
from plugin.data import CARD_POINTS, PLAYED, Game, Group, check_matchday, data_sha256, find_group
from plugin.matches import match_of

# The criteria a team's score is made of, as (name, Record field), each ranking the higher value first.
SCORE = (("points", "points"), ("goal difference", "goal_difference"), ("goals scored", "goals_for"))


@dataclass(frozen=True)
class Record:
    """A team's results over some matches."""

    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    fair_play: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        return 3 * self.won + self.drawn


def records(teams: list[str], games: list[Game]) -> dict[str, Record]:
    """Each of ``teams``' record over the ``games`` among them (all of them must be played)."""
    found = {team: Record() for team in teams}
    for game in games:
        for team, scored, conceded, cards in (
            (game.home, game.home_goals, game.away_goals, game.home_cards),
            (game.away, game.away_goals, game.home_goals, game.away_cards),
        ):
            old = found[team]
            found[team] = Record(
                played=old.played + 1,
                won=old.won + (scored > conceded),
                drawn=old.drawn + (scored == conceded),
                lost=old.lost + (scored < conceded),
                goals_for=old.goals_for + scored,
                goals_against=old.goals_against + conceded,
                fair_play=old.fair_play + sum(count * worth for count, worth in zip(cards, CARD_POINTS, strict=True)),
            )
    return found


def counted(group: Group, through_matchday: int) -> list[Game]:
    return [game for game in group.games if game.status == PLAYED and game.matchday <= through_matchday]


def among(games: list[Game], teams: list[str]) -> list[Game]:
    return [game for game in games if game.home in teams and game.away in teams]


class Table:
    """A group's counted matches and every team's record over them, ranked by one ruleset."""

    def __init__(self, group: Group, games: list[Game]) -> None:
        self.seeds = group.seeds
        self.games = games
        self.teams = list(group.seeds)
        self.overall = records(self.teams, games)

    def mini(self, teams: list[str]) -> dict[str, Record]:
        """Head to head: ``teams``' records over the counted matches among them only."""
        return records(teams, among(self.games, teams))

    @staticmethod
    def score(record: Record) -> tuple[int, int, int]:
        return record.points, record.goal_difference, record.goals_for

    def fifa(self) -> list[str]:
        order: list[str] = []
        level = sorted(self.teams, key=lambda team: self.score(self.overall[team]), reverse=True)
        for _, tied in groupby(level, key=lambda team: self.score(self.overall[team])):
            tied = list(tied)
            head = self.mini(tied)
            order += sorted(
                tied,
                key=lambda team: (
                    *(-value for value in self.score(head[team])),
                    -self.overall[team].fair_play,
                    self.seeds[team],
                ),
            )
        return order

    def uefa(self) -> list[str]:
        level = sorted(self.teams, key=lambda team: self.overall[team].points, reverse=True)
        return [
            team
            for _, tied in groupby(level, key=lambda team: self.overall[team].points)
            for team in self.head_to_head(list(tied))
        ]

    def head_to_head(self, tied: list[str]) -> list[str]:
        """uefa (2)-(5) on a set level on points, then (6)-(9) on a set head to head cannot split."""
        if len(tied) == 1:
            return tied
        head = self.mini(tied)
        ranked = sorted(tied, key=lambda team: self.score(head[team]), reverse=True)
        buckets = [list(bucket) for _, bucket in groupby(ranked, key=lambda team: self.score(head[team]))]
        if len(buckets) == 1:
            return sorted(tied, key=self.overall_key)
        return [team for bucket in buckets for team in self.head_to_head(bucket)]

    def overall_key(self, team: str) -> tuple[int, int, int, int]:
        """uefa (6)-(9): goal difference, goals scored, fair play, then the seed, best first."""
        record = self.overall[team]
        return -record.goal_difference, -record.goals_for, -record.fair_play, self.seeds[team]

    def decider(self, ruleset: Ruleset, upper: str, lower: str) -> str:
        """Why ``upper`` ranks just above ``lower``: the first criterion that tells them apart."""
        steps = self.fifa_steps(upper) if ruleset is Ruleset.FIFA else self.uefa_steps(upper)
        for label, values in steps:
            if values[upper] != values[lower]:
                return f"{upper} over {lower} by {ruleset.value} {label}: {values[upper]} v {values[lower]}"
        raise AssertionError(f"{upper} and {lower} are level on every {ruleset.value} criterion")

    def fifa_steps(self, team: str) -> list[tuple[str, dict[str, int]]]:
        """The fifa criteria as they apply to ``team``, each with every concerned team's value."""
        tied = [other for other in self.teams if self.score(self.overall[other]) == self.score(self.overall[team])]
        head = self.mini(tied)
        names = ", ".join(tied)
        return [
            *(
                (f"{number} {name}", self.values(self.overall, field))
                for number, (name, field) in zip(("(1)", "(2)", "(3)"), SCORE, strict=True)
            ),
            *(
                (f"{number} head-to-head {name} among {names}", self.values(head, field))
                for number, (name, field) in zip(("(4)", "(5)", "(6)"), SCORE, strict=True)
            ),
            ("(7) fair play", self.values(self.overall, "fair_play")),
            ("(8) lower seed", dict(self.seeds)),
        ]

    def uefa_steps(self, team: str) -> list[tuple[str, dict[str, int]]]:
        """The uefa criteria as they apply to ``team``: head to head over its set level on points,
        then (5) over each smaller set still level with it, then the overall criteria."""
        steps = [("(1) points", self.values(self.overall, "points"))]
        tied = [other for other in self.teams if self.overall[other].points == self.overall[team].points]
        numbers = ("(2)", "(3)", "(4)")
        while len(tied) > 1:
            head = self.mini(tied)
            names = ", ".join(tied)
            steps += [
                (f"{number} head-to-head {name} among {names}", self.values(head, field))
                for number, (name, field) in zip(numbers, SCORE, strict=True)
            ]
            still = [other for other in tied if self.score(head[other]) == self.score(head[team])]
            if len(still) == len(tied):
                break
            tied = still
            numbers = ("(5) reapplied",) * 3
        return [
            *steps,
            ("(6) goal difference", self.values(self.overall, "goal_difference")),
            ("(7) goals scored", self.values(self.overall, "goals_for")),
            ("(8) fair play", self.values(self.overall, "fair_play")),
            ("(9) lower seed", dict(self.seeds)),
        ]

    @staticmethod
    def values(found: dict[str, Record], field: str) -> dict[str, int]:
        return {team: getattr(record, field) for team, record in found.items()}


def pin_standings(given: StandingsInput, workspace: Path) -> PinnedStandingsOutput:
    """The correct table for the task, with the matches it counts and the data's sha256."""
    group = find_group(given.tournament, given.group)
    check_matchday(group, given.through_matchday)
    table = Table(group, counted(group, given.through_matchday))
    order = table.fifa() if given.ruleset is Ruleset.FIFA else table.uefa()
    rows = []
    for position, team in enumerate(order, 1):
        record = table.overall[team]
        rows.append(
            Row(
                position=position,
                team=team,
                played=record.played,
                won=record.won,
                drawn=record.drawn,
                lost=record.lost,
                goals_for=record.goals_for,
                goals_against=record.goals_against,
                goal_difference=record.goal_difference,
                points=record.points,
                fair_play=record.fair_play,
            )
        )
    return PinnedStandingsOutput(
        tournament=given.tournament,
        group=given.group,
        through_matchday=given.through_matchday,
        ruleset=given.ruleset,
        rows=rows,
        qualified=order[:2],
        deciders=[table.decider(given.ruleset, upper, lower) for upper, lower in pairwise(order)],
        counted_matches=[match_of(game) for game in table.games],
        data_sha256=data_sha256(),
    )
