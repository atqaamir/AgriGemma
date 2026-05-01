from app.jobs.base_job import BaseJob
from app.agents.coordinator_agent import CoordinatorAgent


"""
Runs daily at 7pm, performs the following:
- Invokes the CoordinatorAgent -> task_generation function
- prints the results to the console (for now, eventually will log to a file or database)
- eventually add retry logic and error handling

"""


class TaskGeneratorJob(BaseJob):

    name = "Task Generator Job"

    def process_target(self, user):

        return CoordinatorAgent.task_generation(
            user_id=user.id
        )