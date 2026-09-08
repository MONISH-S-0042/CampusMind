from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import JobLookupError

from app.db.models import Remainder
from app.services.utilities.time import to_local_time
from app.services.notification.notify import send_remainder

db_url = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5432/campusmind")

IST = ZoneInfo("Asia/Kolkata")

jobstores = {
    "default":SQLAlchemyJobStore(url=db_url)
}

scheduler = BackgroundScheduler(
    jobstores = jobstores,
    timezone = IST
)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("Scheduler started")
        
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped")
        
def schedule_remainder(remainder:Remainder):
    rid = remainder.id
    time = to_local_time(remainder.remainder_time)
    now = datetime.now(IST)
    
    #AT that time
    scheduler.add_job(
            send_remainder,
            trigger="date",
            run_date = time,
            args = [rid,"at_time"],
            id = f"remainder:{rid}:at_time",
            replace_existing=True
        )
    #Before 2 hours
    hour2_before = time - timedelta(hours=2)
    if hour2_before>=now:
        scheduler.add_job(
            send_remainder,
            trigger="date",
            run_date = hour2_before,
            args = [rid,"before_2_hours"],
            id = f"remainder:{rid}:before_2_hours",
            replace_existing=True
        )
    else:
        remove_job_if_exists(f"remainder:{rid}:before_2_hours")
    #1 day before
    day_before = time - timedelta(days=1)
    if day_before>=now:
        scheduler.add_job(
            send_remainder,
            trigger="date",
            run_date = day_before,
            args = [rid,"before_1_day"],
            id = f"remainder:{rid}:before_1_day",
            replace_existing=True
        )
    else:
        remove_job_if_exists(f"remainder:{rid}:before_1_day")
    
    print(f"Scheduled remainder for {remainder.id}")


def remove_job_if_exists(job_id:str):
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        pass
    
def unschedule_remainder(remainder:Remainder):
    rid = remainder.id
    remove_job_if_exists(f"remainder:{rid}:before_1_day")
    remove_job_if_exists(f"remainder:{rid}:before_2_hours")
    remove_job_if_exists(f"remainder:{rid}:at_time")
    print(f"Unscheduled {remainder.id}")