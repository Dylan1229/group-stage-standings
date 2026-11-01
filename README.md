# Group Stage Standings

A `nanoagent.plugin/v0001` plugin with the structure of NanoAgent's reference plugin,
[arxiv-source](https://github.com/zeyuyang8/arxiv-source). Its task, `rank-group`, gives an
agent one group of a football (soccer) tournament, a matchday and a tiebreaker ruleset, `fifa`
or `uefa`. The agent reads the group's results and cards, works out the table (played, won,
drawn, lost, goals, points, fair-play points) and ranks the teams under that ruleset's precisely
stated tiebreakers, then saves the table and submits it. The answer is unique and a rule-based
verifier checks it: eleven named checks, every number recounted by code independent of the
answer key. Everything runs offline on bundled data; the two tournaments, all their teams and all
their results are fictional.

## Tools

| Tool | Does | Code |
|---|---|---|
| `list_tournaments` | Lists the bundled tournaments, each group's teams (best seed first) and its last matchday | `src/plugin/matches.py` |
| `get_group_matches` | One group's teams with their seeds and every match of every matchday: `md`, `status`, `home`, `away`, goals `hg`/`ag` (null when postponed) and cards `hc`/`ac` as `[yellow, second_yellow, red, yellow_red]` | `src/plugin/matches.py` |
| `save_standings` | Writes the table it is given to `standings/<tournament>-<group>-md<N>-<ruleset>.json` (replacing an earlier save) and returns it with that `path`. It checks only the table's shape (1 to 8 rows, positions 1..n in order, different non-blank team names, no negative count, `fair_play` at most 0, `qualified` two different teams of the rows) and computes nothing | `src/plugin/save.py` |
| `pin_standings` | The answer key, never an agent's tool: the table under the ruleset, computed plainly, with a reason for each pair of neighbouring rows (`deciders`), the matches it counted and the sha256 of the data | `src/plugin/standings.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `rank-group` | Ranks a group under the fifa or uefa tiebreakers and saves the table | `agent`, with `list_tournaments`, `get_group_matches` and `save_standings`; reference `pin_standings` |
| `get-group-matches` | Shows a group's teams, seeds and every match with its score and cards | `tool` (`get_group_matches`), judged as that tool's output |

## The task

Input (`StandingsInput`): `tournament` (e.g. `atlantic-cup-2026`), `group` (a letter),
`through_matchday` (1 to the group's last matchday) and `ruleset` (`fifa` or `uefa`). Before the
agent starts, NanoAgent runs `pin_standings` on the input in a scratch workspace; its
`verify_input` refuses an unknown tournament or group and a `through_matchday` out of range, so a
malformed task never reaches an agent.

The plan the instructions prescribe fits RUSH Lab's limits for agent runs (6 model turns, 2,048
tokens per reply, reasoning included): turn 1 `get_group_matches`; turn 2 work out the table and
`save_standings`; turn 3 `submit` exactly what `save_standings` returned; one turn spare to fix a
refused save. `list_tournaments` is offered but not needed. `get_group_matches` returns about 1,300
characters for a 4-team group and 1,800 for the 5-team group, and the table is 3 to 5 rows of
integers.

Output (`StandingsOutput`, what `save_standings` returns): the input echoed; `rows` in rank order,
each `{position, team, played, won, drawn, lost, goals_for, goals_against, goal_difference, points,
fair_play}`; `qualified`, the teams at positions 1 and 2; and `path`, the saved file.

## Rules

Every rule the answer follows, as the task's instructions state it:

- **Counted matches.** Only matches with status `played` and matchday `md <= through_matchday`
  count. A postponed match never counts, so teams can have played different numbers of matches.
  A team with no counted match has a row of zeros.
- **Per team.** `played`, `won`, `drawn`, `lost`, `goals_for`, `goals_against`;
  `goal_difference = goals_for - goals_against`; `points` = 3 per win, 1 per draw, 0 per loss.
- **Fair-play points** (`fair_play`, higher is better, 0 at best): -1 per yellow, -3 per
  second_yellow (a sending-off for a second yellow), -4 per red (a direct red), -5 per yellow_red (a
  yellow then a direct red), summed over the team's own cards in its counted matches. Each booking
  is recorded in exactly one category: a second-yellow sending-off is one `second_yellow`, its
  yellows are not counted again.
- **Direction.** Every criterion ranks the higher value first, except the seed (each team's unique
  pre-tournament ranking), where the smaller number ranks first.
- **Head to head (h2h)** means points, goal difference and goals scored counted only in the counted
  matches between the teams of the set in question.
- **`fifa`:** (1) points, (2) goal difference, (3) goals scored, over all counted matches. Teams
  still level on all three form one set, ranked by (4) h2h points, (5) h2h goal difference, (6) h2h
  goals scored, computed once over the matches among that whole set, never recomputed for a smaller
  part of it; then (7) fair-play points over all counted matches; then (8) the seed.
- **`uefa`:** (1) points. Teams level on points form a set, ranked by (2) h2h points, (3) h2h goal
  difference, (4) h2h goals scored among that set. (5) If that separates some of them but leaves two
  or more level, (2)-(4) apply again over the matches among only those still level, and so on. A set
  that (2)-(4) cannot split at all is ranked by (6) goal difference, (7) goals scored over all counted
  matches, (8) fair-play points, (9) the seed.
- **The table.** `position` runs 1..n in rank order, every team of the group appears once with its
  name as given, and `qualified` lists positions 1 and 2 in that order. Seeds are unique, so the
  order is always total.

## Data

`src/plugin/data/tournaments.json`, sha256
`f3e899518bee264596fea2ddabb2430682b764c7fce5f16283fc393cee0da938` (`tests/test_tools.py` holds the
same value, so a changed file fails the tests; every answer key records the sha256 it read, and the
verifier compares it with the file's). Both tournaments are fictional and the file was written by
hand: there is no generator. Each tournament lists its groups' teams with unique seeds (1 best), and
each match its `id`, `group`, `matchday`, `home`, `away`, `status` (`played` or `postponed`), and, when
played, `home_goals`, `away_goals` and per-team cards (`yellow`, `second_yellow`, `red`, `yellow_red`).
`src/plugin/data.py` refuses the file on load unless every two teams of a group meet exactly once,
no team plays twice on a matchday, seeds run 1..n and a postponed match carries no goals or cards.

The groups are built so that every criterion decides something (checked in `tests/test_standings.py`
against tables worked out by hand):

| Tournament, group | Teams | What it exercises (through the last matchday unless noted) |
|---|---|---|
| `atlantic-cup-2026` A | 4 | No ties at all |
| `atlantic-cup-2026` B | 4 | Galdria and Fenlark on 4 points: fifa ranks Galdria 2nd on goal difference (+3 v 0), uefa ranks Fenlark 2nd on its 1-0 h2h win; the rulesets qualify different teams |
| `atlantic-cup-2026` C | 4 | Three teams on 6 points, +1, 3 goals. H2H puts Istrena 3rd and leaves Jorvale and Kelmora level: uefa (5) reapplies h2h to the two (Kelmora won 2-1), fifa does not and goes to fair play (Jorvale -2 v -3). Matchday 1: fair play and then seed decide; matchday 2: fifa's h2h (4) decides |
| `atlantic-cup-2026` D | 4 | Norvik and Marovia identical down to their 1-1 draw: fair play -3 (three yellows) beats -5 (a yellow and a red, fewer cards). Matchday 1: all four teams on 1 point |
| `atlantic-cup-2026` E | 4 | Sorvane and Rivelle identical down to fair play (-3 each: a second yellow v three yellows): seed 12 beats 18, against alphabetical order |
| `atlantic-cup-2026` F | 4 | Ulmera v Wexmoor postponed (matchday 2): those two have played 2 matches, the others 3 |
| `boreal-trophy-2027` A | 5 | Five matchdays, one team resting each. Cindral and Belmuth on 7 points, +1: fifa on goals scored (5 v 2), uefa on h2h (Belmuth won 1-0); qualification differs. Matchday 1: Arvoren has played nothing |
| `boreal-trophy-2027` B | 3 | Three 1-1 draws: fair play ranks Hesperon first, the seed separates Gaventa and Fyrdal |

## Verifier

`verifier/rank.py` judges a `rank-group` submission with eleven checks, in this order. Each is
`{id, ok, expected, actual, message}` in `details.checks`; `ok` is `true`, `false`, or `null` when a
check it needs failed (the three checks that need the answer key are not run without one). The
verdict is valid only when all eleven hold. `score` is the share of the eleven that hold (a check
not run counts as not holding). `message` is the first failing check's id and message plus how many
more fail, or on success the whole expected table. `details` also holds `rows_correct` (rows equal
to the answer key's, position by position), `expected_order` and the answer key's `deciders`.

| # | id | What it checks | Example failure message |
|---|---|---|---|
| 1 | `reference` | The answer key is present, for this task input, pinned from the bundled file (its sha256), its counted matches are exactly the played matches of matchday 1 to N in the file, each of its rows equals the verifier's own count, its points never rise down the table and its `qualified` is its first two | `No reference: pin_standings did not run for this task` |
| 2 | `echo` | `tournament`, `group`, `through_matchday` and `ruleset` are the task's | `The submission is for another task: it names ruleset 'fifa' (expected 'uefa')` |
| 3 | `saved-file` | `path` is `standings/<tournament>-<group>-md<N>-<ruleset>.json`, the file is inside the workspace (no `..`, absolute path or symlink out), at most 1 MB, UTF-8 JSON, an object | `No file at standings/atlantic-cup-2026-B-md3-uefa.json: call save_standings and submit what it returns` |
| 4 | `file-matches` | The file holds exactly the submission but its `path` (compared as canonical JSON, so `true` is not `1`) | `The saved file differs from the submission in qualified: submit exactly what save_standings returned` |
| 5 | `teams` | The rows name each team of the group exactly once | `The rows must name each of the group's 4 teams once: Harvolt is missing` |
| 6 | `positions` | Positions run 1..n down the rows | `Positions are [1, 2, 2, 4], expected [1, 2, 3, 4]` |
| 7 | `arithmetic` | Each row is consistent: won+drawn+lost = played, points = 3·won + drawn, goal_difference = goals_for − goals_against | `A row contradicts itself: Estoval: points 6, not 3*won+drawn = 7` |
| 8 | `stats` | Each row's nine numbers equal the verifier's own count (`verifier/table.py`) of the answer key's counted matches | `A row's numbers are not the counted matches': Fenlark: fair_play -3 (expected -5)` |
| 9 | `points-order` | Points never rise down the table (true under both rulesets, checked without the answer key) | `Corvenna (3 pts) is below Dalmira (0 pts): points rank first` |
| 10 | `order` | The teams are in the answer key's order for the ruleset; the message gives the answer key's reason | `Position 2 is Galdria, expected Fenlark (Fenlark over Galdria by uefa (2) head-to-head points among Fenlark, Galdria: 3 v 0)` |
| 11 | `qualified` | `qualified` is the answer key's top two, and the submitted rows' first two | `qualified is ['Fenlark', 'Estoval'], expected ['Estoval', 'Fenlark']` |

The verifier never imports `src/`: it reads `tournaments.json` itself (`verifier/data.py`) to check
inputs, tool outputs and the answer key, and counts tables with its own code. A bug in the answer
key's counting is caught by check 1; a bug in its ordering is caught only where it breaks the points
order (see Limitations). `verify_task` never raises on a value that fits the contract: a missing,
oversized, non-JSON, non-UTF-8 or deeply nested file, a path that escapes the workspace, duplicate or
missing rows, empty lists and a missing reference all give `valid: false` with a message.

Every tool call is checked too. `verify_input` refuses an unknown tournament or group, a
`through_matchday` out of range (`get_group_matches`, `save_standings`, `pin_standings`) and a
misshapen table (`save_standings`, the same shape rules the tool applies). `verify_output` holds
`list_tournaments` and `get_group_matches` to the bundled file, `save_standings` to its input and to
the file it wrote, and `pin_standings` to check 1. The `get-group-matches` task is judged as its
tool's output is.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (no network), tools, tasks and the task's instructions
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable names this plugin needs (none)
├── src/plugin/      # the MCP server (__main__.py), the data loader (data.py), the lookups (matches.py),
│                    #   save_standings (save.py), the answer key (standings.py) and data/tournaments.json
├── tests/           # test_standings.py (hand-worked golden tables), test_tools.py, test_verifier.py
├── ui/              # renderers.js draws a StandingsOutput as a table, the qualified rows marked
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: one module per tool, rank.py for the task, its own
                     #   data reader (data.py) and table count (table.py)
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest           # 172 tests, offline
uv run ruff check .
```

Tests are named by category: `test_correct_*` (every group, matchday and ruleset's answer key
table saved and approved; the tools' outputs approved), `test_incorrect_*` (wrong order with right
numbers, a swapped 2nd and 3rd, one wrong number, a self-contradicting row, wrong `qualified`, a
postponed match counted, extra, missing or repeated teams, a file that disagrees with the
submission or was tampered with, a submission for another task), `test_missing_*` (no saved file,
no reference, no rows), `test_malformed_*` (inputs refused, files that are not JSON, not UTF-8,
too large, too deep, a folder, a symlink out, unsafe paths, a tampered answer key, submissions that
break the contract, tool outputs that differ from the data) and `test_boundary_*` (the rulesets
disagreeing and each verdict following its own, uefa's reapplication, matchday 1, fair-play and
seed deciders, a team with no counted match, a postponed match).

NanoAgent passes the folder the plugin may write to as `NANOAGENT_WORKSPACE`; `save_standings`
writes only `standings/` inside it. Run the tool task through NanoAgent (from its checkout):

```bash
# run.yaml:
# _ > nanoagent.cli.plugin.PluginRunConfig:
# plugin: <this folder>
# task: get-group-matches
# arguments: <args.json holding {"tournament": "atlantic-cup-2026", "group": "F"}>
# inputs: []
# timeout: 120.0
uv run nanoagent plugin run config=run.yaml home=<run folder>
```

The agent task runs with `nanoagent plugin agent` and a model. Without one, scripted cases replay
the agent's tool calls through the real MCP server, pin the answer key as NanoAgent does, and hand
the submission to the sandboxed verifier; each case states the outcome it expects. Sixteen cases
(correct, incorrect, missing, malformed, boundary) live outside the plugin, in the course
repository's `evidence/cases/group-stage-standings/`:

```bash
<nanoagent>/.venv/bin/python evidence/replay.py plugins/group-stage-standings evidence/cases/group-stage-standings
```

## Limitations

- **The order comes from the answer key.** The verifier recounts every number itself, but takes
  the tiebreaker order from `pin_standings`; it checks independently only that points never rise
  down the table. An ordering bug in the answer key that kept points in order would pass both.
  `tests/test_standings.py` guards against that with 24 tables worked out by hand, covering every
  criterion of both rulesets.
- **The rulesets are stated, not official.** They follow the shape of FIFA's and UEFA's group
  tiebreakers but are simplified and fixed here (no drawing of lots, no disciplinary points beyond
  the four card kinds, no away-goals or ranking-coefficient criteria); the task's instructions are
  the definition.
- **Small, fictional data.** Two invented tournaments, 32 teams, 49 matches. The agent can only be
  tested on these 26 (group, matchday) pairs, 52 tasks with the ruleset.
- **No partial credit by row.** The score is the share of checks that hold, so a table with one
  wrong row and one with all rows wrong can score alike; `rows_correct` reports the finer measure.
- **One file per task input.** Saving twice replaces the file; two runs of the same task in one
  workspace share it, and the verifier cannot tell which run wrote it.
