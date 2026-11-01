"""The lookups the agent reads the bundled tournaments with: list_tournaments and get_group_matches."""

from __future__ import annotations

from pathlib import Path

from contract import (
    GroupInput,
    GroupMatchesOutput,
    GroupSummary,
    ListTournamentsInput,
    Match,
    MatchStatus,
    TeamSeed,
    TournamentsOutput,
    TournamentSummary,
)
from plugin.data import Game, find_group, tournaments

LEGEND = (
    "md matchday; hg/ag home/away goals (null if postponed); hc/ac home/away cards"
    " [yellow, second_yellow, red, yellow_red]"
)


def match_of(game: Game) -> Match:
    """One match as the tools show it: short keys, cards as [yellow, second_yellow, red, yellow_red]."""
    return Match(
        id=game.id,
        md=game.matchday,
        status=MatchStatus(game.status),
        home=game.home,
        away=game.away,
        hg=game.home_goals,
        ag=game.away_goals,
        hc=list(game.home_cards),
        ac=list(game.away_cards),
    )


def list_tournaments(given: ListTournamentsInput, workspace: Path) -> TournamentsOutput:
    """Every bundled tournament with its groups' teams, best seed first, and last matchdays."""
    return TournamentsOutput(
        tournaments=[
            TournamentSummary(
                id=tournament.id,
                name=tournament.name,
                groups=[
                    GroupSummary(group=letter, last_matchday=group.last_matchday, teams=list(group.seeds))
                    for letter, group in sorted(tournament.groups.items())
                ],
            )
            for tournament in tournaments().values()
        ]
    )


def get_group_matches(given: GroupInput, workspace: Path) -> GroupMatchesOutput:
    """One group's teams with their seeds and every match of every matchday, postponed ones included."""
    group = find_group(given.tournament, given.group)
    return GroupMatchesOutput(
        tournament=group.tournament,
        group=group.letter,
        last_matchday=group.last_matchday,
        legend=LEGEND,
        teams=[TeamSeed(team=team, seed=seed) for team, seed in group.seeds.items()],
        matches=[match_of(game) for game in group.games],
    )
