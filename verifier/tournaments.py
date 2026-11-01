"""list_tournaments: it takes nothing, and must list every bundled tournament as the data holds it."""

from . import data
from .checks import result


def expected():
    return [
        {
            "id": tournament,
            "name": found["name"],
            "groups": [
                {"group": letter, "last_matchday": data.last_matchday(group), "teams": data.teams(group)}
                for letter, group in sorted(found["groups"].items())
            ],
        }
        for tournament, found in data.tournaments().items()
    ]


def verify_input(value):
    return result(True, "list_tournaments takes nothing")


def verify_output(input_value, output_value, workspace):
    listed = [
        {
            "id": tournament.id,
            "name": tournament.name,
            "groups": [
                {"group": group.group, "last_matchday": group.last_matchday, "teams": list(group.teams)}
                for group in tournament.groups
            ],
        }
        for tournament in output_value.tournaments
    ]
    if listed != expected():
        return result(False, "the tournaments listed differ from the bundled data")
    return result(True, f"{len(listed)} tournaments listed as the bundled data holds them", data_sha256=data.sha256())
