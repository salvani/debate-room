"""Progress tracker for debate crew execution."""
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Tuple

from crewai.events import (
    crewai_event_bus,
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
)


@dataclass
class ProgressState:
    """Thread-safe container for progress state."""

    current_task_index: int = 0
    current_status: str = "Initializing debate..."
    is_complete: bool = False
    has_error: bool = False
    error_message: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update(
        self,
        task_index: int = None,
        status: str = None,
        complete: bool = None,
        error: str = None,
    ):
        """Thread-safe state update."""
        with self.lock:
            if task_index is not None:
                self.current_task_index = task_index
            if status is not None:
                self.current_status = status
            if complete is not None:
                self.is_complete = complete
            if error is not None:
                self.has_error = True
                self.error_message = error

    def get_progress(self) -> Tuple[float, str]:
        """Get current progress percentage and status."""
        with self.lock:
            progress = self.current_task_index / 6  # 6 tasks total
            return progress, self.current_status


class EventDrivenProgressTracker:
    """Tracks debate progress using CrewAI events."""

    TASK_INFO = {
        "propose_opening": (0, "Proposition opening statement"),
        "oppose_opening": (1, "Opposition opening statement"),
        "collect_openings": (2, "Collecting opening statements"),
        "propose_rebuttal": (3, "Proposition rebuttal"),
        "oppose_rebuttal": (4, "Opposition rebuttal"),
        "decide": (5, "Judge's decision"),
    }

    def __init__(self, progress_callback: Optional[Callable[[float, str], None]] = None):
        """Initialize event-driven progress tracker.

        Args:
            progress_callback: Function called with (progress_float, status_str)
                               when progress updates occur.
        """
        self.progress_callback = progress_callback
        self.state = ProgressState()

    def _get_task_info(self, task_name: str) -> Tuple[int, str]:
        """Get task index and description from task name."""
        normalized_name = task_name.lower().replace(" ", "_").replace("-", "_")
        for key, (index, desc) in self.TASK_INFO.items():
            if key in normalized_name or normalized_name in key:
                return index, desc
        return -1, task_name  # Fallback

    def _get_task_name_from_event(self, event) -> str:
        """Extract task name from event, checking multiple possible locations."""
        # Try event.task_name first
        if getattr(event, "task_name", None):
            return event.task_name
        # Try event.task.name (where task is the actual Task object)
        task = getattr(event, "task", None)
        if task and getattr(task, "name", None):
            return task.name
        return "unknown"

    def _on_task_started(self, source, event: TaskStartedEvent):
        """Handle task started event."""
        task_name = self._get_task_name_from_event(event)
        index, description = self._get_task_info(task_name)

        status = f"Starting: {description}"
        self.state.update(task_index=index, status=status)

        if self.progress_callback:
            progress, status = self.state.get_progress()
            self.progress_callback(progress, status)

    def _on_task_completed(self, source, event: TaskCompletedEvent):
        """Handle task completed event."""
        task_name = self._get_task_name_from_event(event)
        index, description = self._get_task_info(task_name)

        status = f"Completed: {description}"
        self.state.update(task_index=index + 1, status=status)

        if self.progress_callback:
            progress, status = self.state.get_progress()
            self.progress_callback(progress, status)

    def _on_task_failed(self, source, event: TaskFailedEvent):
        """Handle task failed event."""
        task_name = self._get_task_name_from_event(event)
        error_msg = getattr(event, "error", "Unknown error")
        self.state.update(error=f"Task '{task_name}' failed: {error_msg}")

    def _on_crew_completed(self, source, event: CrewKickoffCompletedEvent):
        """Handle crew completion event."""
        self.state.update(task_index=6, status="Debate complete!", complete=True)
        if self.progress_callback:
            self.progress_callback(1.0, "Debate complete!")

    def _on_crew_failed(self, source, event: CrewKickoffFailedEvent):
        """Handle crew failure event."""
        error_msg = getattr(event, "error", "Unknown error")
        self.state.update(error=f"Debate failed: {error_msg}")

    def register_handlers(self):
        """Register event handlers on the CrewAI event bus."""
        crewai_event_bus.register_handler(TaskStartedEvent, self._on_task_started)
        crewai_event_bus.register_handler(TaskCompletedEvent, self._on_task_completed)
        crewai_event_bus.register_handler(TaskFailedEvent, self._on_task_failed)
        crewai_event_bus.register_handler(CrewKickoffCompletedEvent, self._on_crew_completed)
        crewai_event_bus.register_handler(CrewKickoffFailedEvent, self._on_crew_failed)

    def get_state(self) -> Tuple[float, str, bool, str]:
        """Get current progress state.

        Returns:
            Tuple of (progress, status, has_error, error_message)
        """
        progress, status = self.state.get_progress()
        with self.state.lock:
            return progress, status, self.state.has_error, self.state.error_message


class DebateProgressTracker:
    """Tracks debate progress by monitoring output file creation."""

    OUTPUT_FILES = {
        "01_propose_opening.md": "Proposition opening statement",
        "02_oppose_opening.md": "Opposition opening statement",
        "03_openings_collected.md": "Collecting openings",
        "04_propose_rebuttal.md": "Proposition rebuttal",
        "05_oppose_rebuttal.md": "Opposition rebuttal",
        "06_decide.md": "Judge's decision"
    }

    def __init__(self, output_dir: str = "output"):
        """Initialize progress tracker.

        Args:
            output_dir: Directory where output files are written
        """
        self.output_dir = Path(output_dir)
        self.total_tasks = len(self.OUTPUT_FILES)

    def get_completed_tasks(self) -> list:
        """Get list of completed output files.

        Returns:
            List of completed filenames
        """
        completed = []
        for filename in self.OUTPUT_FILES.keys():
            filepath = self.output_dir / filename
            # File exists and has content (not just created empty)
            if filepath.exists() and filepath.stat().st_size > 0:
                completed.append(filename)
        return completed

    def get_progress(self) -> Tuple[float, str]:
        """Get current progress percentage and status message.

        Returns:
            Tuple of (progress_percentage, status_message)
        """
        completed = self.get_completed_tasks()
        completed_count = len(completed)
        progress = (completed_count / self.total_tasks) * 100

        # Determine current status message
        if completed_count == 0:
            status = "Starting debate crew..."
        elif completed_count < self.total_tasks:
            # Find the next expected task
            next_task_index = completed_count
            next_file = list(self.OUTPUT_FILES.keys())[next_task_index]
            next_task_name = self.OUTPUT_FILES[next_file]
            status = f"Working on: {next_task_name}"
        else:
            status = "Debate complete!"

        return progress, status

    def monitor_progress(self, poll_interval: float = 1.5) -> Optional[Tuple[float, str]]:
        """Monitor progress and yield updates.

        Args:
            poll_interval: Seconds between polling checks

        Yields:
            Tuple of (progress_percentage, status_message)
        """
        last_progress = -1

        while True:
            progress, status = self.get_progress()

            # Always yield to keep Gradio progress bar active
            # even if progress hasn't changed
            yield progress, status
            last_progress = progress

            # Stop if complete
            if progress >= 100:
                break

            time.sleep(poll_interval)

    def clear_output_dir(self):
        """Clear all output files before starting new debate."""
        if self.output_dir.exists():
            for filename in self.OUTPUT_FILES.keys():
                filepath = self.output_dir / filename
                if filepath.exists():
                    filepath.unlink()
