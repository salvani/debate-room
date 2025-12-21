"""Progress tracker for debate crew execution."""
import time
from pathlib import Path
from typing import Tuple, Optional


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
