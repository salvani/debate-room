# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CrewAI-based debate system that simulates formal debates using AI agents. The system creates two debaters who argue for and against a motion, followed by a judge who evaluates the arguments and declares a winner.

### Core Architecture

The project uses CrewAI's multi-agent framework with a sequential process flow:

1. **Agents** (`src/debate_room/config/agents.yaml`):
   - `debater`: A compelling debater who argues both for and against the motion
   - `judge`: An impartial judge who evaluates arguments based on merit

2. **Tasks** (`src/debate_room/config/tasks.yaml`):
   - `propose_opening`: Debater presents opening arguments IN FAVOR of the motion
   - `oppose_opening`: Debater presents opening arguments AGAINST the motion
   - `collect_openings`: Gathers both opening statements
   - `propose_rebuttal`: Proposition side responds to opposition arguments
   - `oppose_rebuttal`: Opposition side responds to proposition arguments
   - `decide`: Judge evaluates all arguments and declares winner with preference degree (low/medium/high/absolute)

3. **Crew Configuration** (`src/debate_room/crew.py`):
   - Uses `@CrewBase` decorator pattern from CrewAI
   - Agents and tasks are auto-wired using `@agent` and `@task` decorators
   - Runs in sequential process mode (openings → rebuttals → decide)
   - Both agents use `gemini/gemini-3-pro-preview` LLM

4. **Execution** (`src/debate_room/main.py`):
   - Entry point defines the debate motion as input
   - Kicks off crew execution and prints raw result
   - Default motion: "The solution to the trolley problem is to stick to your path, whatever it may be."

### Why Crew (Not Flow)?

CrewAI offers two abstractions: **Crews** (autonomous agents collaborating) and **Flows** (event-driven sequential/branching steps). This project uses a Crew because:

- Debate naturally fits the agent-based model with distinct debater/judge roles
- We want creative, autonomous argument generation rather than rigid templates
- `Process.sequential` provides sufficient ordering control

A Flow would be preferable for conditional branching, direct LLM calls without agent overhead, or production pipelines. Consider **Flows orchestrating Crews** for complex workflows requiring both creativity and precise control.

### Output Structure

Debate results are written to the `output/` directory:
- `output/01_propose_opening.md`: Proposition opening statement
- `output/02_oppose_opening.md`: Opposition opening statement
- `output/03_openings_collected.md`: Combined opening statements
- `output/04_propose_rebuttal.md`: Proposition rebuttal
- `output/05_oppose_rebuttal.md`: Opposition rebuttal
- `output/06_decide.md`: Judge's decision with preference rating

## Prerequisites

- Python >=3.10, <3.14 (specified in `pyproject.toml`)
- `uv` package manager (install with `pip install uv`)
- Google Gemini API key
- CrewAI 1.7.0 with `google-genai` and `tools` extras

## Development Commands

### Running the Project

```bash
# Run the debate crew with default motion
crewai run

# Alternative using the entry point
python -m debate_room.main
```

### Dependency Management

This project uses `uv` for dependency management:

```bash
# Install dependencies (if not already done)
crewai install

# Or manually with uv
uv sync
```

### Environment Setup

Required environment variables in `.env`:
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Required for Google Gemini API access
- `OPENAI_API_KEY`: May be required by CrewAI framework dependencies
- `MODEL`: Set to `gemini/gemini-3-pro-preview` (default model for agents)
- `ANTHROPIC_API_KEY`: Optional, if using Claude models

### Project Scripts

Available via `pyproject.toml`:
- `debate_room` or `run_crew`: Run the main debate (CLI)
- `debate_gui`: Run the Gradio web interface

## Key Implementation Details

### Agent Configuration Pattern

The crew uses YAML-based configuration with CrewAI's decorator pattern:
- Agents are defined in `agents.yaml` and loaded via `@agent` decorator
- Tasks reference agents by name and are loaded via `@task` decorator
- The `{motion}` template variable is interpolated from the inputs dictionary

### GUI Interface

The project includes a Gradio-based web interface (`src/debate_room/app.py`):
- Interactive motion input
- Real-time progress tracking
- View all debate outputs (openings, rebuttals, judge's decision)
- Progress monitoring via background threads

## Adding New Features

### To modify the debate motion:
Edit the `inputs` dictionary in `src/debate_room/main.py` or use the GUI interface

### To add new agents:
1. Add agent definition to `config/agents.yaml` with role, goal, backstory, and llm
2. Create `@agent` method in `crew.py` returning `Agent(config=self.agents_config['agent_name'], verbose=True)`
3. The agent will be automatically added to `self.agents` via the decorator

### To add new tasks:
1. Add task definition to `config/tasks.yaml` with description, expected_output, agent, and optional output_file
2. Create `@task` method in `crew.py` returning `Task(config=self.tasks_config['task_name'])`
3. The task will be automatically added to `self.tasks` via the decorator
4. Tasks execute in the order they are defined when using sequential process

### To modify debate flow:
Change `Process.sequential` to `Process.hierarchical` in `crew.py` for manager-based task delegation
