"""Gradio GUI for the debate system."""
import threading
import time
from pathlib import Path
import gradio as gr

from crewai.events import crewai_event_bus

from .crew import DebateRoom
from .progress_tracker import DebateProgressTracker, EventDrivenProgressTracker
from gradio.themes.utils import fonts


# Map radio button selections to output files
SPEECH_TO_FILE = {
    "Proposition Opening": "output/01_propose_opening.md",
    "Opposition Opening": "output/02_oppose_opening.md",
    "Proposition Rebuttal": "output/04_propose_rebuttal.md",
    "Opposition Rebuttal": "output/05_oppose_rebuttal.md",
    "Judge's Decision": "output/06_decide.md"
}

DEFAULT_MOTION = "The solution to the trolley problem is to stick to your path, whatever it may be."


def load_markdown_output(selected_speech: str) -> str:
    """Load and return the markdown content for the selected speech.

    Args:
        selected_speech: The radio button selection

    Returns:
        Markdown content or error message
    """
    if selected_speech not in SPEECH_TO_FILE:
        return "Please select a speech to view."

    filepath = Path(SPEECH_TO_FILE[selected_speech])

    if not filepath.exists():
        return f"**No output available yet.**\n\nThe debate has not been run or this output file was not generated.\n\nPlease run a debate first by entering a motion and clicking 'Start Debate'."

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            return "**Output file is empty.**\n\nThe debate may still be in progress."
        return content
    except Exception as e:
        return f"**Error loading output:**\n\n{str(e)}"


def run_debate_with_progress(motion: str, progress=gr.Progress()):
    """Run the debate crew with progress tracking.

    Args:
        motion: The debate motion
        progress: Gradio progress tracker

    Returns:
        Tuple of (status_message, updated_markdown_content)
    """
    if not motion or not motion.strip():
        return "Please enter a debate motion.", load_markdown_output("Judge's Decision")

    # Clear old output files using the legacy tracker
    legacy_tracker = DebateProgressTracker(output_dir="output")
    legacy_tracker.clear_output_dir()

    # Initialize event-driven tracker (no callback - we'll poll state instead)
    tracker = EventDrivenProgressTracker()

    # Shared state for crew execution
    crew_result = [None]
    crew_error = [None]
    crew_done = threading.Event()

    def run_crew():
        """Run the crew in a background thread."""
        try:
            with crewai_event_bus.scoped_handlers():
                tracker.register_handlers()
                crew_result[0] = DebateRoom().crew().kickoff(inputs={'motion': motion})
        except Exception as e:
            crew_error[0] = e
        finally:
            crew_done.set()

    # Start crew in background thread
    crew_thread = threading.Thread(target=run_crew, daemon=True)
    crew_thread.start()

    # Show initial progress
    progress(0, desc="Starting debate crew...")

    # Poll tracker state and update Gradio progress until crew is done
    last_status = ""
    while not crew_done.is_set():
        prog, status, has_error, error_msg = tracker.get_state()
        if status != last_status:
            progress(prog, desc=status)
            last_status = status
        time.sleep(0.3)  # Poll interval

    # Wait for thread to fully complete
    crew_thread.join(timeout=5)

    # Final progress update
    progress(1.0, desc="Debate complete!")

    # Check for crew execution errors
    if crew_error[0]:
        return f"**Error running debate:**\n\n{str(crew_error[0])}", load_markdown_output("Judge's Decision")

    # Check for errors captured during execution
    _, _, has_error, error_msg = tracker.get_state()
    if has_error:
        return f"**Debate completed with warnings:**\n\n{error_msg}", load_markdown_output("Judge's Decision")

    # Load the judge's decision to display
    judge_output = load_markdown_output("Judge's Decision")

    return (
        "**Debate completed successfully!**\n\n"
        "The judge's decision is shown below. Use the radio buttons to view other speeches.",
        judge_output
    )


def create_gradio_interface():
    """Create and return the Gradio interface.

    Returns:
        gr.Blocks interface
    """
    with gr.Blocks(title="Debate Room", theme=gr.themes.Origin(
        font = (
            fonts.GoogleFont("Source Pro"),
            "ui-serif",
            "system-ui",
            "serif",
        )
    )) as interface:
        gr.Markdown("# Debate Room")
        gr.Markdown("Enter a motion to debate and watch AI agents argue for and against it.")

        with gr.Row():
            with gr.Column():
                motion_input = gr.Textbox(
                    label="Debate Motion",
                    placeholder="Enter the motion to debate...",
                    lines=4,
                    value=DEFAULT_MOTION
                )

                start_button = gr.Button("Start Debate", variant="primary", size="lg")

                status_output = gr.Markdown("")

        gr.Markdown("---")

        with gr.Row():
            with gr.Column(scale=1):
                speech_selector = gr.Radio(
                    choices=list(SPEECH_TO_FILE.keys()),
                    label="Select Speech to View",
                    value="Judge's Decision",
                    interactive=True
                )

            with gr.Column(scale=2):
                markdown_output = gr.Markdown(
                    load_markdown_output("Judge's Decision"),
                    label="Output"
                )

        # Event handlers
        def on_start_debate(motion):
            """Handle start debate button click."""
            status, judge_content = run_debate_with_progress(motion)
            return status, judge_content

        start_button.click(
            fn=on_start_debate,
            inputs=[motion_input],
            outputs=[status_output, markdown_output]
        )

        speech_selector.change(
            fn=load_markdown_output,
            inputs=[speech_selector],
            outputs=[markdown_output]
        )

    return interface


def launch():
    """Launch the Gradio interface."""
    interface = create_gradio_interface()
    interface.launch()


if __name__ == "__main__":
    launch()
