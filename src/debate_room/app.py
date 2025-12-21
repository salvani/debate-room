"""Gradio GUI for the debate system."""
import threading
from pathlib import Path
import gradio as gr

from .crew import DebateRoom
from .progress_tracker import DebateProgressTracker
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

    # Initialize progress tracker
    tracker = DebateProgressTracker(output_dir="output")

    # Clear old output files before starting new debate
    tracker.clear_output_dir()

    # Track progress in a separate thread
    progress_complete = threading.Event()
    last_progress = [0, "Starting debate..."]

    def update_progress():
        """Update progress in background thread."""
        for prog, status in tracker.monitor_progress(poll_interval=1.5):
            last_progress[0] = prog
            last_progress[1] = status
            progress(prog / 100, desc=status)

    # Start progress monitoring in background
    progress_thread = threading.Thread(target=update_progress, daemon=True)
    progress_thread.start()

    try:
        # Run the debate (progress updates handled by background thread)
        result = DebateRoom().crew().kickoff(inputs={'motion': motion})

        # Wait for progress thread to complete
        progress_thread.join(timeout=5)

        progress(1.0, desc="Debate complete!")

        # Load the judge's decision to display
        judge_output = load_markdown_output("Judge's Decision")

        return f"**Debate completed successfully!**\n\nThe judge's decision is shown below. Use the radio buttons to view other speeches.", judge_output

    except Exception as e:
        return f"**Error running debate:**\n\n{str(e)}", load_markdown_output("Judge's Decision")


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
