# app/jobs/base_job.py

from datetime import datetime

from app.services.domain_service.user_service import UserService


"""
TEMPLATE METHOD FOR BACKGROUND JOBS
"""


class BaseJob:

    name = "Base Job"
    seperator = "-" * 70

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
        print(f"{self.name.center(70)}")
        print(self.seperator)

        targets = self.get_targets()

        print(f"{'Targets Found:'.ljust(30)} {len(targets)}")
        print(f"{'Started At:'.ljust(30)} {started_at.isoformat()}")

        results = []

        successful_targets = 0
        failed_targets = 0

        for target in targets:

            print("\n" + "-" * 70)

            print(f"{'Processing Target ID:'.ljust(30)} {target.id}")

            try:

                result = self.process_target(target)

                successful_targets += 1

                results.append({
                    "target_id": target.id,
                    "execution_status": "success",
                    "result": result,
                })

                print(f"{'Execution Status:'.ljust(30)} SUCCESS")

            except Exception as e:

                failed_targets += 1

                results.append({
                    "target_id": target.id,
                    "execution_status": "failed",
                    "error": str(e),
                })

                print(f"{'Execution Status:'.ljust(30)} FAILED")
                print(f"{'Error:'.ljust(30)} {str(e)}")

        completed_at = datetime.utcnow()

        print("\n" + self.seperator)

        print(f"{'Completed Job:'.ljust(30)} {self.name}")
        print(f"{'Successful Targets:'.ljust(30)} {successful_targets}")
        print(f"{'Failed Targets:'.ljust(30)} {failed_targets}")
        print(f"{'Completed At:'.ljust(30)} {completed_at.isoformat()}")

        print(self.seperator)

        return {
            "job_name": self.name,
            "execution_status": "completed",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "successful_targets": successful_targets,
            "failed_targets": failed_targets,
            "results": results,
        }