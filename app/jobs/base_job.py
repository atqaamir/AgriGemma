# app/jobs/base_job.py

from datetime import datetime
from utils.enums_ import Status

from app.services.domain_service.user_service import UserService


"""
TEMPLATE METHOD FOR BACKGROUND JOBS
"""


class BaseJob:

    name = "Base Job"
    seperator = "-" * 70
    padding = 30
    widthCenter = 70

    def get_targets(self):
        """
        Override if needed.
        """
        return UserService.get_all_users()

    def process_target(self, target):
        """
        MUST be implemented by subclasses.
        """
        raise NotImplementedError

    def run(self):

        started_at = datetime.utcnow()

        print("\n" + self.seperator)
        print(f"{self.name.center(self.widthCenter)}")
        print(self.seperator)

        targets = self.get_targets()

        print(f"{'Targets Found:'.ljust(self.padding)} {len(targets)}")
        print(f"{'Started At:'.ljust(self.padding)} {started_at.isoformat()}")

        results = []

        successful_targets = 0
        failed_targets = 0

        for target in targets:

            print("\n" + self.seperator)

            print(f"{'Processing Target ID:'.ljust(self.padding)} {target.id}")

            try:

                result = self.process_target(target)

                successful_targets += 1

                results.append({
                    "target_id": target.id,
                    "execution_status": Status.SUCCESS,
                    "result": result,
                })

                print(f"{'Execution Status:'.ljust(self.padding)} SUCCESS")

            except Exception as e:

                failed_targets += 1

                results.append({
                    "target_id": target.id,
                    "execution_status": Status.FAILED,
                    "error": str(e),
                })

                print(f"{'Execution Status:'.ljust(self.padding)} FAILED")
                print(f"{'Error:'.ljust(self.padding)} {str(e)}")

        completed_at = datetime.utcnow()

        print("\n" + self.seperator)

        print(f"{'Completed Job:'.ljust(self.padding)} {self.name}")
        print(f"{'Successful Targets:'.ljust(self.padding)} {successful_targets}")
        print(f"{'Failed Targets:'.ljust(self.padding)} {failed_targets}")
        print(f"{'Completed At:'.ljust(self.padding)} {completed_at.isoformat()}")

        print(self.seperator)

        return {
            "job_name": self.name,
            "execution_status": Status.COMPLETED,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "successful_targets": successful_targets,
            "failed_targets": failed_targets,
            "results": results,
        }