from app import create_app
from app.jobs.weekly_plan_job import WeeklyUpdateJob
from app.jobs.daily_update_job import DailyUpdateJob


def testrun_all_jobs():
    app = create_app()

    with app.app_context():
        # print("\n[~] Running Forecast Refresh Job...")
        # forecast_results = ForecastRefreshJob.run()
        # print(forecast_results)

        print("\n[*] Running Weekly Update Job...")
        weekly_results = WeeklyUpdateJob.run()
        print(weekly_results)

        print("\n[*] Running Daily Update Job...")
        daily_results = DailyUpdateJob.run()
        print(daily_results)


if __name__ == "__main__":
    testrun_all_jobs()