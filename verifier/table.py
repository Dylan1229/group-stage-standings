"""The verifier's own count of a group table from a list of matches, independent of src/plugin/standings.py."""

from .checks import STATS

# Fair-play points lost per card, in the order a match lists its cards: yellow, second_yellow, red, yellow_red.
CARD_COST = (1, 3, 4, 5)


def recount(teams, matches):
    """team -> {stat: value} over ``matches`` (plain dicts with home, away, hg, ag, hc, ac, all played)."""
    lines = {team: dict.fromkeys(STATS, 0) for team in teams}
    for match in matches:
        sides = (
            (match["home"], match["hg"], match["ag"], match["hc"]),
            (match["away"], match["ag"], match["hg"], match["ac"]),
        )
        for team, scored, conceded, cards in sides:
            line = lines.setdefault(team, dict.fromkeys(STATS, 0))
            line["played"] += 1
            if scored > conceded:
                line["won"] += 1
            elif scored == conceded:
                line["drawn"] += 1
            else:
                line["lost"] += 1
            line["goals_for"] += scored
            line["goals_against"] += conceded
            line["fair_play"] -= sum(count * cost for count, cost in zip(cards, CARD_COST))
    for line in lines.values():
        line["goal_difference"] = line["goals_for"] - line["goals_against"]
        line["points"] = 3 * line["won"] + line["drawn"]
    return lines


def row_differences(row, expected):
    """``row``'s (a plain row) stats that differ from ``expected``'s, as "name actual (expected value)"."""
    return [f"{name} {row[name]} (expected {expected[name]})" for name in STATS if row[name] != expected[name]]


def arithmetic_problem(row):
    """Why a plain row contradicts itself, or None: W+D+L=P, points=3W+D, GD=GF-GA."""
    problems = []
    if row["won"] + row["drawn"] + row["lost"] != row["played"]:
        problems.append(f"won+drawn+lost = {row['won'] + row['drawn'] + row['lost']}, not played {row['played']}")
    if row["points"] != 3 * row["won"] + row["drawn"]:
        problems.append(f"points {row['points']}, not 3*won+drawn = {3 * row['won'] + row['drawn']}")
    if row["goal_difference"] != row["goals_for"] - row["goals_against"]:
        problems.append(
            f"goal_difference {row['goal_difference']}, not goals_for-goals_against"
            f" = {row['goals_for'] - row['goals_against']}"
        )
    return "; ".join(problems) or None
