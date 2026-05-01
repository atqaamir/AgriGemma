
from app.agents.coordinator_agent import CoordinatorAgent

"""
Runs daily at 5am, performs the following:
- Invokes the CoordinatorAgent -> daily_update function
- prints the results to the console (for now, eventually will log to a file or database)
- eventually add retry logic and error handling

"""
from app.jobs.base_job import BaseJob
from app.agents.coordinator_agent import CoordinatorAgent


class DailyUpdateJob(BaseJob):

    name = "Daily Update Job"

    def process_target(self, user):

        return CoordinatorAgent.daily_update(
            user_id=user.id
        )