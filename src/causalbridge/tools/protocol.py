from typing import Protocol

from causalbridge.schemas import RuntimeCase, ToolRequest, ToolResult


class ToolBackend(Protocol):
    """Anish's adapter must use only the supplied visible RuntimeCase.

    Return the exact request with a finite float (numeric operations), bool
    (structural operations), or an explicit error. Do not load oracle files.
    """

    def execute(self, request: ToolRequest, case: RuntimeCase) -> ToolResult: ...
