"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_TOURNAMENTS = "list_tournaments"
    GET_GROUP_MATCHES = "get_group_matches"
    SAVE_STANDINGS = "save_standings"
    PIN_STANDINGS = "pin_standings"


class Task(Enum):
    RANK_GROUP = "rank-group"
    GET_GROUP_MATCHES = "get-group-matches"


class Ruleset(Enum):
    FIFA = "fifa"
    UEFA = "uefa"


class MatchStatus(Enum):
    PLAYED = "played"
    POSTPONED = "postponed"


TOURNAMENT = "The tournament id, as list_tournaments gives it, e.g. atlantic-cup-2026"
GROUP = "The group's letter, e.g. B"
THROUGH_MATCHDAY = "Count only matches of matchday 1 to this one, inclusive: 1 to the group's last matchday"
RULESET = "The tiebreaker ruleset: fifa or uefa"
HOME_CARDS = (
    "The home team's cards as [yellow, second_yellow, red, yellow_red], worth -1, -3, -4 and -5 fair-play"
    " points each; [0, 0, 0, 0] when postponed"
)
AWAY_CARDS = (
    "The away team's cards as [yellow, second_yellow, red, yellow_red], worth -1, -3, -4 and -5 fair-play"
    " points each; [0, 0, 0, 0] when postponed"
)
ROWS = "One row per team of the group, in rank order, best first"
QUALIFIED = "The teams at positions 1 and 2, in that order"


@dataclass
class ListTournamentsInput(Output):
    """list_tournaments takes nothing."""


@dataclass
class GroupSummary(Output):
    group: Annotated[str, GROUP]
    last_matchday: Annotated[int, "The group's last matchday"]
    teams: Annotated[list[str], "The group's teams, best seed first"]


@dataclass
class TournamentSummary(Output):
    id: Annotated[str, "The tournament id"]
    name: Annotated[str, "The tournament's name"]
    groups: Annotated[list[GroupSummary], "Its groups, by letter"]


@dataclass
class TournamentsOutput(Output):
    tournaments: Annotated[list[TournamentSummary], "Every bundled tournament (all fictional)"]


@dataclass
class GroupInput(Output):
    tournament: Annotated[str, TOURNAMENT]
    group: Annotated[str, GROUP]


@dataclass
class TeamSeed(Output):
    team: Annotated[str, "The team's name"]
    seed: Annotated[int, "Its pre-tournament ranking, unique in the tournament: 1 is the best"]


@dataclass
class Match(Output):
    id: Annotated[str, "The match id, e.g. B3"]
    md: Annotated[int, "Its matchday"]
    status: Annotated[MatchStatus, "played, or postponed: a postponed match never counts"]
    home: Annotated[str, "The home team"]
    away: Annotated[str, "The away team"]
    hg: Annotated[int | None, "Home goals; null when postponed"]
    ag: Annotated[int | None, "Away goals; null when postponed"]
    hc: Annotated[list[int], HOME_CARDS]
    ac: Annotated[list[int], AWAY_CARDS]


@dataclass
class GroupMatchesOutput(Output):
    tournament: Annotated[str, TOURNAMENT]
    group: Annotated[str, GROUP]
    last_matchday: Annotated[int, "The group's last matchday"]
    legend: Annotated[str, "What each match field means"]
    teams: Annotated[list[TeamSeed], "The group's teams, best seed first"]
    matches: Annotated[list[Match], "Every match of the group, all matchdays, by matchday"]


@dataclass
class Row(Output):
    position: Annotated[int, "1 to the number of teams, top first"]
    team: Annotated[str, "The team's name, as get_group_matches gives it"]
    played: Annotated[int, "Counted matches played"]
    won: Annotated[int, "Counted matches won"]
    drawn: Annotated[int, "Counted matches drawn"]
    lost: Annotated[int, "Counted matches lost"]
    goals_for: Annotated[int, "Goals scored in counted matches"]
    goals_against: Annotated[int, "Goals conceded in counted matches"]
    goal_difference: Annotated[int, "goals_for - goals_against"]
    points: Annotated[int, "3 per win + 1 per draw"]
    fair_play: Annotated[int, "-(yellow + 3*second_yellow + 4*red + 5*yellow_red) over counted matches; 0 or less"]


@dataclass
class StandingsInput(Output):
    tournament: Annotated[str, TOURNAMENT]
    group: Annotated[str, GROUP]
    through_matchday: Annotated[int, THROUGH_MATCHDAY]
    ruleset: Annotated[Ruleset, RULESET]


@dataclass
class SaveInput(Output):
    tournament: Annotated[str, TOURNAMENT]
    group: Annotated[str, GROUP]
    through_matchday: Annotated[int, THROUGH_MATCHDAY]
    ruleset: Annotated[Ruleset, RULESET]
    rows: Annotated[list[Row], ROWS]
    qualified: Annotated[list[str], QUALIFIED]


@dataclass
class StandingsOutput(Output):
    tournament: Annotated[str, TOURNAMENT]
    group: Annotated[str, GROUP]
    through_matchday: Annotated[int, THROUGH_MATCHDAY]
    ruleset: Annotated[Ruleset, RULESET]
    rows: Annotated[list[Row], ROWS]
    qualified: Annotated[list[str], QUALIFIED]
    path: Annotated[str, "The saved file, standings/<tournament>-<group>-md<through_matchday>-<ruleset>.json"]


@dataclass
class PinnedStandingsOutput(Output):
    tournament: Annotated[str, TOURNAMENT]
    group: Annotated[str, GROUP]
    through_matchday: Annotated[int, THROUGH_MATCHDAY]
    ruleset: Annotated[Ruleset, RULESET]
    rows: Annotated[list[Row], "The correct table, in rank order"]
    qualified: Annotated[list[str], QUALIFIED]
    deciders: Annotated[list[str], "For each pair of neighbouring rows, the criterion that puts the upper team first"]
    counted_matches: Annotated[list[Match], "The matches the table counts: played, matchday <= through_matchday"]
    data_sha256: Annotated[str, "The sha256 of the bundled tournaments.json the table was computed from"]


TOOLS = {
    Tool.LIST_TOURNAMENTS: (ListTournamentsInput, TournamentsOutput),
    Tool.GET_GROUP_MATCHES: (GroupInput, GroupMatchesOutput),
    Tool.SAVE_STANDINGS: (SaveInput, StandingsOutput),
    Tool.PIN_STANDINGS: (StandingsInput, PinnedStandingsOutput),
}
TASKS = {
    Task.RANK_GROUP: (StandingsInput, StandingsOutput),
    Task.GET_GROUP_MATCHES: (GroupInput, GroupMatchesOutput),
}
