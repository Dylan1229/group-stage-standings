"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import matches, pin, rank, save, tournaments

TOOLS = {
    Tool.LIST_TOURNAMENTS: tournaments,
    Tool.GET_GROUP_MATCHES: matches,
    Tool.SAVE_STANDINGS: save,
    Tool.PIN_STANDINGS: pin,
}


def _tool_output(module):
    """A tool task's check: its output judged as its one tool's verify_output judges it."""
    return lambda arguments, output, reference, workspace: module.verify_output(arguments, output, workspace)


# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {
    Task.RANK_GROUP: rank.verify_task,
    Task.GET_GROUP_MATCHES: _tool_output(matches),
}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
