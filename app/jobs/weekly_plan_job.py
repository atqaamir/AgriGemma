from app.jobs.base_job import BaseJob
from app.agents.coordinator_agent import CoordinatorAgent


"""
Runs weekly on Monday at 3.30am, performs the following:
- Invokes the CoordinatorAgent -> weekly_planning function
- prints the results to the console (for now, eventually will log to a file or database)
- eventually add retry logic and error handling

"""


class WeeklyPlanJob(BaseJob):

    name = "Weekly Plan Job"

    def process_target(self, user):

        return CoordinatorAgent.weekly_planning(
            user_id=user.id
        )