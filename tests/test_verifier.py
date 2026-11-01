"""The verifier, called as NanoAgent calls it: every value built into its contract class from JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import TASKS, TOOLS, GroupInput, PinnedStandingsOutput, Ruleset, SaveInput, StandingsInput, Task, Tool
from plugin import get_group_matches, list_tournaments, pin_standings, save_standings
from plugin.data import tournaments

ATLANTIC = "atlantic-cup-2026"
BOREAL = "boreal-trophy-2027"
EVERY_TASK = [
    (tid, letter, through, ruleset)
    for tid, tournament in tournaments().items()
    for letter, group in sorted(tournament.groups.items())
    for through in range(1, group.last_matchday + 1)
    for ruleset in ("fifa", "uefa")
]
CHECKS = [
    "reference",
    "echo",
    "saved-file",
    "file-matches",
    "teams",
    "positions",
    "arithmetic",
    "stats",
    "points-order",
    "order",
    "qualified",
]


def task(tournament: str = ATLANTIC, group: str = "B", through: int = 3, ruleset: str = "uefa") -> dict:
    return {"tournament": tournament, "group": group, "through_matchday": through, "ruleset": ruleset}


def pinned(arguments: dict) -> dict:
    return plain_output(pin_standings(build_output(arguments, StandingsInput), Path(".")))


def saved(
    arguments: dict, workspace: Path, *, rows: list[dict] | None = None, qualified: list[str] | None = None
) -> dict:
    """What save_standings returns for a table (the answer key's unless given), as the agent submits it."""
    key = pinned(arguments)
    given = arguments | {
        "rows": key["rows"] if rows is None else rows,
        "qualified": key["qualified"] if qualified is None else qualified,
    }
    return plain_output(save_standings(build_output(given, SaveInput), workspace))


def verify(arguments: dict, output: dict, workspace: Path, reference: dict | None | str = "pin") -> dict:
    given, made = TASKS[Task.RANK_GROUP]
    reference = pinned(arguments) if reference == "pin" else reference
    pinned_reference = None if reference is None else build_output(reference, PinnedStandingsOutput)
    verdict = verifier.verify_task(
        "rank-group", build_output(arguments, given), build_output(output, made), pinned_reference, str(workspace)
    )
    json.dumps(verdict)  # every verdict is plain JSON
    assert 0.0 <= verdict["score"] <= 1.0
    return verdict


def failing(verdict: dict) -> list[str]:
    return [check["id"] for check in verdict["details"]["checks"] if check["ok"] is not True]


def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def swapped(rows: list[dict], first: int, second: int) -> list[dict]:
    """``rows`` with two rows' places exchanged and positions renumbered: every row keeps its numbers."""
    rows = [dict(row) for row in rows]
    rows[first], rows[second] = rows[second], rows[first]
    return [row | {"position": position} for position, row in enumerate(rows, 1)]


# --- correct ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(("tournament", "group", "through", "ruleset"), EVERY_TASK)
def test_correct_the_saved_answer_key_table_passes_every_check(
    tmp_path: Path, tournament: str, group: str, through: int, ruleset: str
) -> None:
    arguments = task(tournament, group, through, ruleset)
    verdict = verify(arguments, saved(arguments, tmp_path), tmp_path)
    assert verdict["valid"] is True and verdict["score"] == 1.0, verdict["message"]
    assert [check["id"] for check in verdict["details"]["checks"]] == CHECKS
    assert verdict["message"].startswith("All 11 checks hold")


def test_correct_verdict_is_the_same_twice(tmp_path: Path) -> None:
    arguments = task()
    output = saved(arguments, tmp_path) | {"qualified": ["Estoval", "Galdria"]}
    assert verify(arguments, output, tmp_path) == verify(arguments, output, tmp_path)


def test_correct_each_tool_s_output_is_approved(tmp_path: Path) -> None:
    listed = plain_output(list_tournaments(build_output({}, TOOLS[Tool.LIST_TOURNAMENTS][0]), tmp_path))
    assert verifier.verify_output(
        "list_tournaments", None, build_output(listed, TOOLS[Tool.LIST_TOURNAMENTS][1]), str(tmp_path)
    )["valid"]
    group = {"tournament": ATLANTIC, "group": "F"}
    shown = plain_output(get_group_matches(GroupInput(**group), tmp_path))
    given, made = TOOLS[Tool.GET_GROUP_MATCHES]
    assert verifier.verify_output(
        "get_group_matches", build_output(group, given), build_output(shown, made), str(tmp_path)
    )["valid"]
    # The tool task get-group-matches is judged as its tool is.
    assert verifier.verify_task(
        "get-group-matches", build_output(group, given), build_output(shown, made), None, str(tmp_path)
    )["valid"]
    arguments = task()
    output = saved(arguments, tmp_path)
    save_input = build_output({k: v for k, v in output.items() if k != "path"}, SaveInput)
    assert verifier.verify_output(
        "save_standings", save_input, build_output(output, TOOLS[Tool.SAVE_STANDINGS][1]), str(tmp_path)
    )["valid"]
    key = build_output(pinned(arguments), PinnedStandingsOutput)
    assert verifier.verify_output("pin_standings", build_output(arguments, StandingsInput), key, str(tmp_path))["valid"]


# --- incorrect -------------------------------------------------------------------------------------


def test_incorrect_stats_right_but_order_wrong(tmp_path: Path) -> None:
    arguments = task(group="A")
    rows = swapped(pinned(arguments)["rows"], 2, 3)  # Dalmira (0 pts) above Corvenna (3 pts)
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows), tmp_path)
    assert verdict["valid"] is False
    assert failing(verdict) == ["points-order", "order"]
    assert "Dalmira" in verdict["details"]["checks"][9]["message"]


def test_incorrect_swapped_pair_at_two_and_three_changes_who_qualifies(tmp_path: Path) -> None:
    arguments = task(group="D", ruleset="fifa")
    rows = swapped(pinned(arguments)["rows"], 1, 2)  # Marovia above Norvik: fewer cards, more points lost
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows, qualified=["Ostrenna", "Marovia"]), tmp_path)
    assert failing(verdict) == ["order", "qualified"]
    assert verdict["message"].startswith(
        "order: Position 2 is Marovia, expected Norvik (Norvik over Marovia by fifa (7) fair play: -3 v -5)"
    )
    assert verdict["details"]["rows_correct"] == "2/4"


def test_incorrect_order_right_but_one_stat_wrong(tmp_path: Path) -> None:
    arguments = task()
    rows = pinned(arguments)["rows"]
    rows[1]["fair_play"] = -3  # Fenlark has -5
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows), tmp_path)
    assert failing(verdict) == ["stats"]
    assert (
        verdict["message"] == "stats: A row's numbers are not the counted matches': Fenlark: fair_play -3 (expected -5)"
    )
    assert verdict["score"] == pytest.approx(10 / 11)


def test_incorrect_row_that_contradicts_itself(tmp_path: Path) -> None:
    arguments = task()
    rows = pinned(arguments)["rows"]
    rows[0]["points"] = 6  # Estoval: 2 wins and a draw are 7 points
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows), tmp_path)
    assert failing(verdict) == ["arithmetic", "stats"]
    assert "points 6, not 3*won+drawn = 7" in verdict["message"]


def test_incorrect_qualified_that_is_not_the_first_two(tmp_path: Path) -> None:
    arguments = task()
    verdict = verify(arguments, saved(arguments, tmp_path, qualified=["Fenlark", "Estoval"]), tmp_path)
    assert failing(verdict) == ["qualified"]
    assert "expected ['Estoval', 'Fenlark']" in verdict["message"]


def test_incorrect_postponed_match_counted_as_a_draw(tmp_path: Path) -> None:
    arguments = task(group="F", ruleset="fifa")
    rows = pinned(arguments)["rows"]
    for row in rows:
        if row["team"] in ("Ulmera", "Wexmoor"):
            row |= {"played": 3, "drawn": row["drawn"] + 1, "points": row["points"] + 1}
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows), tmp_path)
    assert "stats" in failing(verdict) and "arithmetic" not in failing(verdict)
    assert "Ulmera: played 3 (expected 2)" in verdict["message"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda rows: rows + [rows[-1] | {"position": 5, "team": "Atlantis"}],
            "Atlantis is not a team of the group",
        ),
        (lambda rows: rows[:3], "Harvolt is missing"),
        (lambda rows: rows[:3] + [rows[2] | {"position": 4}], "Harvolt is missing"),
    ],
)
def test_incorrect_extra_missing_or_repeated_team(tmp_path: Path, change, message: str) -> None:
    arguments = task()
    rows = change(pinned(arguments)["rows"])
    output = saved(arguments, tmp_path) | {"rows": rows}
    (tmp_path / output["path"]).write_text(json.dumps({k: v for k, v in output.items() if k != "path"}))
    verdict = verify(arguments, output, tmp_path)
    assert "teams" in failing(verdict) and message in verdict["message"]


def test_incorrect_submission_disagrees_with_the_saved_file(tmp_path: Path) -> None:
    arguments = task()
    output = saved(arguments, tmp_path)
    output["rows"] = swapped(output["rows"], 1, 2)
    verdict = verify(arguments, output, tmp_path)
    assert failing(verdict) == ["file-matches", "order", "qualified"]
    assert verdict["message"].startswith("file-matches: The saved file differs from the submission in rows")


def test_incorrect_saved_file_tampered_after_saving(tmp_path: Path) -> None:
    arguments = task()
    output = saved(arguments, tmp_path)
    path = tmp_path / output["path"]
    tampered = json.loads(path.read_text())
    tampered["rows"][0]["won"] = True  # JSON true is not the integer 1
    tampered["qualified"] = ["Estoval", "Galdria"]
    path.write_text(json.dumps(tampered))
    verdict = verify(arguments, output, tmp_path)
    assert failing(verdict) == ["file-matches"]
    assert "in qualified, rows" in verdict["message"]


@pytest.mark.parametrize(
    ("echo", "differs"),
    [
        ({"ruleset": "fifa"}, "ruleset 'fifa'"),
        ({"through_matchday": 2}, "through_matchday 2"),
        ({"group": "C"}, "group 'C'"),
    ],
)
def test_incorrect_submission_for_another_task(tmp_path: Path, echo: dict, differs: str) -> None:
    arguments = task()
    output = saved(arguments, tmp_path) | echo
    verdict = verify(arguments, output, tmp_path)
    assert verdict["message"].startswith(f"echo: The submission is for another task: it names {differs}")
    assert "file-matches" in failing(verdict)


# --- boundary --------------------------------------------------------------------------------------


@pytest.mark.parametrize(("tournament", "group", "through"), [(ATLANTIC, "B", 3), (ATLANTIC, "C", 3), (BOREAL, "A", 5)])
def test_boundary_the_rulesets_disagree_and_each_verdict_follows_its_own(
    tmp_path: Path, tournament: str, group: str, through: int
) -> None:
    fifa, uefa = task(tournament, group, through, "fifa"), task(tournament, group, through, "uefa")
    fifa_rows, uefa_rows = pinned(fifa)["rows"], pinned(uefa)["rows"]
    assert [row["team"] for row in fifa_rows] != [row["team"] for row in uefa_rows]
    assert verify(fifa, saved(fifa, tmp_path, rows=fifa_rows), tmp_path)["valid"] is True
    assert verify(uefa, saved(uefa, tmp_path, rows=uefa_rows), tmp_path)["valid"] is True
    wrong = saved(uefa, tmp_path, rows=fifa_rows, qualified=pinned(fifa)["qualified"])
    assert failing(verify(uefa, wrong, tmp_path)) == ["order", "qualified"]
    wrong = saved(fifa, tmp_path, rows=uefa_rows, qualified=pinned(uefa)["qualified"])
    assert failing(verify(fifa, wrong, tmp_path)) == ["order", "qualified"]


def test_boundary_uefa_reapplication_is_what_separates_two_of_three(tmp_path: Path) -> None:
    arguments = task(group="C", ruleset="uefa")
    rows = swapped(pinned(arguments)["rows"], 0, 1)  # fifa's fair-play order: Jorvale first
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows, qualified=["Jorvale", "Kelmora"]), tmp_path)
    assert "(5) reapplied head-to-head points among Jorvale, Kelmora: 3 v 0" in verdict["message"]


def test_boundary_matchday_one_ties_ranked_by_seed_alone_fail(tmp_path: Path) -> None:
    arguments = task(group="C", through=1, ruleset="fifa")
    rows = swapped(pinned(arguments)["rows"], 0, 1)  # Istrena (seed 3) over Jorvale: fair play comes first
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows, qualified=["Istrena", "Jorvale"]), tmp_path)
    assert failing(verdict) == ["order", "qualified"]
    assert "fifa (7) fair play: -1 v -2" in verdict["message"]


def test_boundary_full_identity_ranked_alphabetically_fails_on_seed(tmp_path: Path) -> None:
    arguments = task(group="E", ruleset="uefa")
    rows = swapped(pinned(arguments)["rows"], 1, 2)  # Rivelle before Sorvane, as the alphabet has it
    verdict = verify(arguments, saved(arguments, tmp_path, rows=rows, qualified=["Quenra", "Rivelle"]), tmp_path)
    assert "uefa (9) lower seed: 12 v 18" in verdict["message"]


def test_boundary_team_without_a_counted_match_has_a_row_of_zeros(tmp_path: Path) -> None:
    arguments = task(BOREAL, "A", 1, "uefa")
    rows = pinned(arguments)["rows"]
    assert rows[3] == {
        "position": 4,
        "team": "Arvoren",
        **dict.fromkeys(
            ("played", "won", "drawn", "lost", "goals_for", "goals_against", "goal_difference", "points", "fair_play"),
            0,
        ),
    }
    assert verify(arguments, saved(arguments, tmp_path, rows=rows), tmp_path)["valid"] is True


# --- missing ---------------------------------------------------------------------------------------


def test_missing_saved_file(tmp_path: Path) -> None:
    arguments = task()
    output = saved(arguments, tmp_path / "elsewhere")
    verdict = verify(arguments, output, tmp_path)
    assert failing(verdict) == ["saved-file", "file-matches"]
    assert verdict["message"] == (
        "saved-file: No file at standings/atlantic-cup-2026-B-md3-uefa.json: call save_standings and submit what it returns"
    )
    assert verdict["details"]["checks"][3]["ok"] is None


def test_missing_reference(tmp_path: Path) -> None:
    arguments = task()
    verdict = verify(arguments, saved(arguments, tmp_path), tmp_path, reference=None)
    assert verdict["valid"] is False and failing(verdict) == ["reference", "stats", "order", "qualified"]
    assert verdict["message"] == "reference: No reference: pin_standings did not run for this task"
    assert [
        check["ok"] for check in verdict["details"]["checks"] if check["id"] in ("stats", "order", "qualified")
    ] == [None] * 3


def test_missing_rows(tmp_path: Path) -> None:
    arguments = task()
    output = saved(arguments, tmp_path) | {"rows": [], "qualified": []}
    verdict = verify(arguments, output, tmp_path)
    assert {"file-matches", "teams", "positions", "order", "qualified"} <= set(failing(verdict))


# --- malformed -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (task(tournament="nowhere-cup"), "unknown tournament 'nowhere-cup'"),
        (task(group="G"), "has no group 'G'"),
        (task(group="b"), "has no group 'b'"),
        (task(through=0), "through_matchday must be 1 to 3"),
        (task(through=4), "through_matchday must be 1 to 3"),
        (task(BOREAL, "A", 6), "through_matchday must be 1 to 5"),
        (task(BOREAL, "B", 4), "through_matchday must be 1 to 3"),
    ],
)
def test_malformed_task_input_is_refused_before_any_agent_runs(value: dict, message: str) -> None:
    verdict = verify_input("pin_standings", value)
    assert verdict["valid"] is False and message in verdict["message"]
    assert verify_input("save_standings", value | {"rows": [], "qualified": []})["valid"] is False


def test_malformed_lookups_are_refused() -> None:
    assert verify_input("list_tournaments", {})["valid"] is True
    assert verify_input("get_group_matches", {"tournament": ATLANTIC, "group": "F"})["valid"] is True
    assert verify_input("get_group_matches", {"tournament": ATLANTIC, "group": "Z"})["valid"] is False
    assert verify_input("get_group_matches", {"tournament": "", "group": "A"})["valid"] is False


@pytest.mark.parametrize(
    ("index", "change", "message"),
    [
        (1, {"position": 1}, "positions must be 1, 2, 3"),
        (1, {"team": "Estoval"}, "different team"),
        (2, {"lost": -1}, "lost cannot be negative"),
        (3, {"fair_play": 1}, "fair_play is 0 or negative"),
    ],
)
def test_malformed_save_input_is_refused(index: int, change: dict, message: str) -> None:
    value = task() | {"rows": pinned(task())["rows"], "qualified": ["Estoval", "Fenlark"]}
    value["rows"][index] |= change
    verdict = verify_input("save_standings", value)
    assert verdict["valid"] is False and message in verdict["message"]
    refused = verify_input(
        "save_standings", task() | {"rows": pinned(task())["rows"], "qualified": ["Estoval", "Nobody"]}
    )
    assert refused["valid"] is False


@pytest.mark.parametrize(
    "content",
    [b"{not json", b"[1, 2]", "é".encode("latin-1"), b"{" * 100_000 + b"}" * 100_000, b" " * 1_000_001],
    ids=["not-json", "a-list", "not-utf8", "deeply-nested", "oversized"],
)
def test_malformed_saved_file_is_refused(tmp_path: Path, content: bytes) -> None:
    arguments = task()
    output = saved(arguments, tmp_path)
    (tmp_path / output["path"]).write_bytes(content)
    verdict = verify(arguments, output, tmp_path)
    assert failing(verdict) == ["saved-file", "file-matches"]


def test_malformed_saved_file_that_is_a_folder_is_refused(tmp_path: Path) -> None:
    arguments = task()
    output = saved(arguments, tmp_path / "elsewhere")
    (tmp_path / output["path"]).mkdir(parents=True)
    assert failing(verify(arguments, output, tmp_path)) == ["saved-file", "file-matches"]


@pytest.mark.parametrize(
    "path",
    [
        "../standings/atlantic-cup-2026-B-md3-uefa.json",
        "/etc/passwd",
        "",
        "standings/other.json",
        "standings/../x.json",
    ],
)
def test_malformed_path_is_refused_without_reading_it(tmp_path: Path, path: str) -> None:
    arguments = task()
    output = saved(arguments, tmp_path) | {"path": path}
    verdict = verify(arguments, output, tmp_path)
    assert failing(verdict) == ["saved-file", "file-matches"]
    assert "expected standings/atlantic-cup-2026-B-md3-uefa.json" in verdict["message"]


def test_malformed_saved_file_linked_outside_the_workspace_is_refused(tmp_path: Path) -> None:
    arguments = task()
    workspace = tmp_path / "workspace"
    output = saved(arguments, tmp_path / "outside")
    (workspace / "standings").mkdir(parents=True)
    (workspace / output["path"]).symlink_to(tmp_path / "outside" / output["path"])
    verdict = verify(arguments, output, workspace)
    assert "leads outside the workspace" in verdict["message"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda key: key | {"data_sha256": "0" * 64}, "pinned from other data"),
        (lambda key: key | {"counted_matches": key["counted_matches"][:-1]}, "counted matches are not"),
        (lambda key: key | {"ruleset": "fifa"}, "for another task"),
        (lambda key: key | {"rows": swapped(key["rows"], 0, 3)}, "ranks a team above one with more points"),
        (lambda key: key | {"qualified": ["Estoval", "Galdria"]}, "qualified are not its first two"),
        (
            lambda key: key | {"rows": [row | {"goals_for": row["goals_for"] + 1} for row in key["rows"]]},
            "row is wrong",
        ),
    ],
)
def test_malformed_reference_is_refused(tmp_path: Path, change, message: str) -> None:
    arguments = task()
    reference = change(pinned(arguments))
    verdict = verify(arguments, saved(arguments, tmp_path), tmp_path, reference=reference)
    assert verdict["valid"] is False and failing(verdict)[0] == "reference" and message in verdict["message"]
    given = build_output(arguments, StandingsInput)
    assert (
        verifier.verify_output("pin_standings", given, build_output(reference, PinnedStandingsOutput), str(tmp_path))[
            "valid"
        ]
        is False
    )


def test_malformed_submission_does_not_fit_the_output_contract(tmp_path: Path) -> None:
    output = saved(task(), tmp_path)
    for broken in (
        output | {"rows": [output["rows"][0] | {"points": "seven"}]},
        output | {"ruleset": "concacaf"},
        {key: value for key, value in output.items() if key != "path"},
        output | {"rows": [output["rows"][0] | {"points": 7.5}]},
    ):
        with pytest.raises(ValueError):
            build_output(broken, TASKS[Task.RANK_GROUP][1])


def test_malformed_tool_outputs_are_refused(tmp_path: Path) -> None:
    group = {"tournament": ATLANTIC, "group": "F"}
    given, made = TOOLS[Tool.GET_GROUP_MATCHES]
    shown = plain_output(get_group_matches(GroupInput(**group), tmp_path))
    shown["matches"][2] |= {"status": "played", "hg": 0, "ag": 0}  # the postponed match shown as a 0-0
    assert (
        verifier.verify_output(
            "get_group_matches", build_output(group, given), build_output(shown, made), str(tmp_path)
        )["valid"]
        is False
    )
    output = saved(task(), tmp_path)
    save_input = build_output({k: v for k, v in output.items() if k != "path"}, SaveInput)
    (tmp_path / output["path"]).write_text("{}")
    made = TOOLS[Tool.SAVE_STANDINGS][1]
    assert (
        verifier.verify_output("save_standings", save_input, build_output(output, made), str(tmp_path))["valid"]
        is False
    )
    other = build_output(output | {"ruleset": Ruleset.FIFA.value}, made)
    assert verifier.verify_output("save_standings", save_input, other, str(tmp_path))["valid"] is False
