from dataclasses import dataclass
from typing import Callable


@dataclass
class TaskResult:
    success: bool
    message: str
    iterations: int


class EngineeringLoop:
    """حلقه کنترل‌شده برنامه‌ریزی، پیاده‌سازی، تست و اصلاح."""

    def __init__(self, max_iterations: int = 8):
        self.max_iterations = max_iterations

    def run(
        self,
        task: str,
        implement: Callable[[str], None],
        test: Callable[[], tuple[bool, str]],
    ) -> TaskResult:
        """وظیفه را اجرا می‌کند و تا موفقیت یا رسیدن به سقف تکرار ادامه می‌دهد."""
        feedback = ""
        for iteration in range(1, self.max_iterations + 1):
            instruction = task if not feedback else f"{task}\n\nبازخورد تست:\n{feedback}"
            implement(instruction)
            passed, feedback = test()
            if passed:
                return TaskResult(True, "همه بررسی‌های اعتبارسنجی با موفقیت انجام شد.", iteration)
        return TaskResult(
            False,
            feedback or "حداکثر تعداد تلاش‌های مهندسی به پایان رسید.",
            self.max_iterations,
        )
