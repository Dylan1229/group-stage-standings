// How this plugin's page draws a rank-group result: the table, best first, with the two
// qualified teams marked, and a line naming the group, the matchday and the ruleset.
import { dataTable, h, icon } from "./kit/components.js";

const COLUMNS = [
  { key: "position", label: "Pos", numeric: true },
  { key: "team", label: "Team", primary: true },
  { key: "played", label: "P", numeric: true },
  { key: "won", label: "W", numeric: true },
  { key: "drawn", label: "D", numeric: true },
  { key: "lost", label: "L", numeric: true },
  { key: "goals_for", label: "GF", numeric: true },
  { key: "goals_against", label: "GA", numeric: true },
  { key: "goal_difference", label: "GD", numeric: true },
  { key: "points", label: "Pts", numeric: true },
  { key: "fair_play", label: "FP", numeric: true },
];

export default {
  StandingsOutput: ({ tournament, group, through_matchday, ruleset, rows, qualified }) =>
    h(
      "div",
      { class: "standings" },
      h(
        "p",
        { class: "standings-note muted" },
        icon("check", { size: 16 }),
        `${tournament}, group ${group}, through matchday ${through_matchday}, ${ruleset} tiebreakers: ${qualified.join(" and ")} qualify`,
      ),
      dataTable({
        columns: COLUMNS,
        rows,
        caption: `Group ${group} table`,
        rowClass: (row) => (qualified.includes(row.team) ? "qualified" : ""),
      }).element,
    ),
};
