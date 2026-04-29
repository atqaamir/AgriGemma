from apscheduler.schedulers.background import BackgroundScheduler

from app.jobs.daily_update_job import DailyUpdateJob
from app.jobs.weekly_plan_job import WeeklyPlanJob
# from app.jobs.forecast_refresh_job import ForecastRefreshJob
from app.jobs.task_generator_job import TaskGeneratorJob


scheduler = BackgroundScheduler()


def start_scheduler(app):

    # DAILY UPDATE JOB -> 5 am every day
    scheduler.add_job(
        func=lambda: run_with_context(app, DailyUpdateJob.run),
        trigger="cron",
        hour=5,
        minute=0,
        id="daily_update_job",
        replace_existing=True,
    )

    # DAILY UPDATE JOB -> 7pm every day
    scheduler.add_job(
        func=lambda: run_with_context(app, taskGenerator.run),
        trigger="cron",
        hour=19,
        minute=0,
        id="task_generator_job",
        replace_existing=True,
    )


    # # FORECAST REFRESH JOB
    # scheduler.add_job(
    #     func=lambda: run_with_context(app, ForecastRefreshJob.run),
    #     trigger="interval",
    #     minutes=30,
    #     id="forecast_refresh_job",
    #     replace_existing=True,
    # )

    # WEEKLY PLANNING JOB
    scheduler.add_job(
        func=lambda: run_with_context(app, WeeklyPlanJob.run),
        trigger="cron",
        day_of_week="mon",
        hour=3,
        minute=30,
        id="weekly_plan_job",
        replace_existing=True,
    )

    scheduler.start()

    print("✅ Scheduler started")


def run_with_context(app, job_func):

    with app.app_context():

        print(f"\n🚀 Running job: {job_func.__name__}")

        job_func()