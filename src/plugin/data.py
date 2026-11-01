"""The bundled tournaments (src/plugin/data/tournaments.json): loaded once, checked as they load."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA = Path(__file__).with_name("data") / "tournaments.json"
CARD_KINDS = ("yellow", "second_yellow", "red", "yellow_red")
# Fair-play points per card of each kind, in CARD_KINDS order.
CARD_POINTS = (-1, -3, -4, -5)
PLAYED = "played"
POSTPONED = "postponed"


@dataclass(frozen=True)
class Game:
    id: str
    matchday: int
    home: str
    away: str
    status: str
    home_goals: int | None
    away_goals: int | None
    home_cards: tuple[int, int, int, int]
    away_cards: tuple[int, int, int, int]


@dataclass(frozen=True)
class Group:
    tournament: str
    letter: str
    seeds: dict[str, int]  # team -> seed, best seed first
    games: tuple[Game, ...]  # by matchday, then as listed

    @property
    def last_matchday(self) -> int:
        return max(game.matchday for game in self.games)


@dataclass(frozen=True)
class Tournament:
    id: str
    name: str
    groups: dict[str, Group]  # by letter


def data_sha256() -> str:
    return hashlib.sha256(DATA.read_bytes()).hexdigest()


def _cards(raw: dict, where: str) -> tuple[int, int, int, int]:
    if set(raw) != set(CARD_KINDS) or not all(type(raw[kind]) is int and raw[kind] >= 0 for kind in CARD_KINDS):
        raise ValueError(f"{where}: cards must count {', '.join(CARD_KINDS)} as non-negative integers")
    return tuple(raw[kind] for kind in CARD_KINDS)


def _game(raw: dict, seeds: dict[str, int]) -> Game:
    where = f"match {raw['id']}"
    if raw["home"] not in seeds or raw["away"] not in seeds or raw["home"] == raw["away"]:
        raise ValueError(f"{where}: both teams must be two different teams of its group")
    if type(raw["matchday"]) is not int or raw["matchday"] < 1:
        raise ValueError(f"{where}: matchday must be an integer from 1")
    if raw["status"] == POSTPONED:
        if {"home_goals", "away_goals", "home_cards", "away_cards"} & set(raw):
            raise ValueError(f"{where}: a postponed match has no goals and no cards")
        return Game(raw["id"], raw["matchday"], raw["home"], raw["away"], POSTPONED, None, None, (0,) * 4, (0,) * 4)
    if raw["status"] != PLAYED:
        raise ValueError(f"{where}: status must be {PLAYED} or {POSTPONED}")
    goals = raw["home_goals"], raw["away_goals"]
    if not all(type(value) is int and value >= 0 for value in goals):
        raise ValueError(f"{where}: goals must be non-negative integers")
    return Game(
        raw["id"],
        raw["matchday"],
        raw["home"],
        raw["away"],
        PLAYED,
        *goals,
        _cards(raw["home_cards"], where),
        _cards(raw["away_cards"], where),
    )


def _group(tournament: str, raw: dict, matches: list[dict]) -> Group:
    seeds = {entry["team"]: entry["seed"] for entry in sorted(raw["teams"], key=lambda entry: entry["seed"])}
    games = tuple(
        sorted((_game(match, seeds) for match in matches if match["group"] == raw["group"]), key=lambda g: g.matchday)
    )
    where = f"{tournament} group {raw['group']}"
    pairs = [frozenset((game.home, game.away)) for game in games]
    if len(seeds) < 2 or len(set(pairs)) != len(pairs) or len(pairs) != len(seeds) * (len(seeds) - 1) // 2:
        raise ValueError(f"{where}: every two teams must meet exactly once")
    for matchday in {game.matchday for game in games}:
        playing = [team for game in games if game.matchday == matchday for team in (game.home, game.away)]
        if len(set(playing)) != len(playing):
            raise ValueError(f"{where}: matchday {matchday} gives a team two matches")
    return Group(tournament, raw["group"], seeds, games)


@cache
def tournaments() -> dict[str, Tournament]:
    """Every bundled tournament by id, its data checked: unique seeds, ids and pairings."""
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    found: dict[str, Tournament] = {}
    for entry in raw["tournaments"]:
        seeds = [team["seed"] for group in entry["groups"] for team in group["teams"]]
        ids = [match["id"] for match in entry["matches"]]
        if sorted(seeds) != list(range(1, len(seeds) + 1)) or len(set(ids)) != len(ids):
            raise ValueError(f"{entry['id']}: seeds must be 1 to the number of teams, and match ids unique")
        groups = {group["group"]: _group(entry["id"], group, entry["matches"]) for group in entry["groups"]}
        if sum(len(group.games) for group in groups.values()) != len(entry["matches"]):
            raise ValueError(f"{entry['id']}: every match must belong to one of its groups")
        found[entry["id"]] = Tournament(entry["id"], entry["name"], groups)
    return found


def find_group(tournament: str, group: str) -> Group:
    """The group, or a ValueError naming what exists."""
    known = tournaments()
    if tournament not in known:
        raise ValueError(f"unknown tournament {tournament!r}: one of {', '.join(sorted(known))}")
    groups = known[tournament].groups
    if group not in groups:
        raise ValueError(f"{tournament} has no group {group!r}: groups {', '.join(sorted(groups))}")
    return groups[group]


def check_matchday(group: Group, through_matchday: int) -> None:
    if not 1 <= through_matchday <= group.last_matchday:
        raise ValueError(
            f"through_matchday must be 1 to {group.last_matchday} for {group.tournament} group {group.letter},"
            f" not {through_matchday}"
        )
