from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class DebateRoom:
    """Debate crew"""


    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def debater(self) -> Agent:
        return Agent(config=self.agents_config['debater'], verbose=True)

    @agent
    def judge(self) -> Agent:
        return Agent(config=self.agents_config['judge'], verbose=True)

    @task
    def propose_opening(self) -> Task:
        return Task(config=self.tasks_config['propose_opening'])

    @task
    def oppose_opening(self) -> Task:
        return Task(config=self.tasks_config['oppose_opening'])

    @task
    def collect_openings(self) -> Task:
        return Task(config=self.tasks_config['collect_openings'])

    @task
    def propose_rebuttal(self) -> Task:
        return Task(config=self.tasks_config['propose_rebuttal'])

    @task
    def oppose_rebuttal(self) -> Task:
        return Task(config=self.tasks_config['oppose_rebuttal'])

    @task
    def decide(self) -> Task:
        return Task(config=self.tasks_config['decide'])


    @crew
    def crew(self) -> Crew:
        """Creates the Debate crew"""

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
