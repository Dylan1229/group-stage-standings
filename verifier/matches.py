"""get_group_matches: a known group, shown exactly as the bundled data holds it (every match, postponed too)."""

from . import data
from .checks import plain_match, result


def verify_input(value):
    problem = data.input_problem(value.tournament, value.group)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    found = data.group(input_value.tournament, input_value.group)
    if found is None:
        return result(False, data.input_problem(input_value.tournament, input_value.group))
    if (output_value.tournament, output_value.group) != (input_value.tournament, input_value.group):
        return result(False, "the output names another group than the input")
    if output_value.last_matchday != data.last_matchday(found):
        return result(False, f"last_matchday is {output_value.last_matchday}, expected {data.last_matchday(found)}")
    if [(team.team, team.seed) for team in output_value.teams] != found["teams"]:
        return result(False, "the teams or seeds differ from the bundled data")
    shown = [plain_match(match) for match in output_value.matches]
    if shown != found["matches"]:
        wrong = [match["id"] for match in shown if match not in found["matches"]]
        return result(False, "the matches differ from the bundled data", differing=wrong)
    return result(True, f"{len(shown)} matches shown as the bundled data holds them", data_sha256=data.sha256())
