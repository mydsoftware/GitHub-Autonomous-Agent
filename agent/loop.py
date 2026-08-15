from dataclasses import dataclass
from typing import Callable


@dataclass
class TaskResult:
    success: bool
    message: str
    iterations: int


class EngineeringLoop:
    """Controlled plan -> implement -> test -> repair loop.

    Provider-specific AI calls will be plugged into this interface in the next phase.
    """

    def __init__(self, max_iterations: int = 8):
        self.max_iterations = max_iterations

    def run(
        self,
        task: str,
        implement: Callable[[str], None],
        test: Callable[[], tuple[bool, str]],
    ) -> TaskResult:
        feedback = ""
        for iteration in range(1, self.max_iterations + 1):
            instruction = task if not feedback else f"{task}\n\nTest feedback:\n{feedback}"
            implement(instruction)
            passed, feedback = test()
            if passed:
                return TaskResult(True, "All validation checks passed.", iteration)
        return TaskResult(False, feedback or "Maximum engineering iterations reached.", self.max_iterations)
