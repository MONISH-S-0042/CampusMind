from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()
IST = ZoneInfo("Asia/Kolkata")
def to_local_time(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)

def is_past_date(date):
    return to_local_time(date) <= datetime.now(IST)