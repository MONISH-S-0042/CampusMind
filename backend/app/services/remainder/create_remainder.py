import re
from datetime import datetime
from zoneinfo import ZoneInfo
from langgraph.types import Command, interrupt
from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from app.db.database import session
from app.services.utilities.time import IST, is_past_date, to_local_time
from app.services.utilities.cancel_remainder_operation import is_cancel, cancelled_command
from app.services.notification.scheduler import schedule_remainder
load_dotenv()
import dateparser

def clean_weekday_modifiers(text: str) -> str:
    return re.sub(
        r'\b(next|this|coming|upcoming)\s+(?=monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        '',
        text,
        flags=re.IGNORECASE
    )

def check_time(state: State):
    """Checks the time field before creating a remainder

    Returns:
        Command: Updates 'remainder_data' and routes explicitly to the next node.
    """

    data = state['remainder_data']

    if data.get('remainder_time') is None or data.get('time_mentioned') is False:
        prompt = data.pop('retry_message', None) or "What time should this reminder be set for? (or 'cancel' to stop)"
        answer = interrupt(prompt)
        if is_cancel(answer):
            return cancelled_command("Okay, I've cancelled the operation.")

        cleaned = clean_weekday_modifiers(str(answer))
        parsed = dateparser.parse(
            cleaned,
            settings={'RELATIVE_BASE': datetime.now(IST), 'PREFER_DATES_FROM': 'future'}
        )
        parsed = to_local_time(parsed) if parsed is not None else None
        if parsed is None:
            data['retry_message'] = f"I could not understand {answer} as a date/time, kindly rephrase it (or 'cancel' to stop)"
            return Command(goto="check_time", update={"remainder_data": data})
        if is_past_date(parsed):
            data['retry_message'] = "This date is in the past, kindly enter a future date (or 'cancel' to stop)"
            return Command(goto="check_time", update={"remainder_data": data})
        data['remainder_time'] = parsed

    elif is_past_date(data['remainder_time']):
        data['retry_message'] = "This date is in the past, kindly enter a future date (or 'cancel' to stop)"
        data['remainder_time'] = None
        return Command(goto="check_time", update={"remainder_data": data})

    data.pop('retry_message', None)
    return Command(goto="check_course", update={"remainder_data": data})


def check_course(state: State):
    """Checks the course field before creating a remainder

    Returns:
        Command: Updates 'remainder_data' and routes explicitly to the next node.
    """
    data = state['remainder_data']
    if not data.get('course_name'):
        answer = interrupt("Which course is this remainder for? (or 'cancel' to stop)")
        if is_cancel(answer):
            return cancelled_command("Okay, I've cancelled the operation.")
        data['course_name'] = answer
    return Command(goto="check_extra", update={"remainder_data": data})


def check_extra(state: State):
    """Asks/checks for extra data before creating a remainder

    Returns:
        Command: Updates 'remainder_data' and routes explicitly to the next node.
    """
    data = state['remainder_data']
    if not data.get('event_type') and not data.get('extra_info'):
        answer = interrupt(
            "Any additional details for this remainder — event type (quiz/assignment/etc.) "
            "or extra notes? Say 'skip' if none, or 'cancel' to stop."
        )
        if is_cancel(answer):
            return cancelled_command("Okay, I've cancelled the operation.")
        if str(answer).strip().lower() not in ("skip", "no", "none", ""):
            data['extra_info'] = answer
    return Command(goto="confirm_remainder", update={"remainder_data": data})


def confirm_remainder(state: State):
    """Confirmation before creating a remainder

    Returns:
        Command: Updates 'tool_response' and routes explicitly to the next node.
    """
    data = state['remainder_data']
    summary = (
        f"Please confirm: {data.get('event_type') or 'remainder'} for {data['course_name']} "
        f"at {to_local_time(data['remainder_time']).strftime("%d %B %Y at %I:%M %p")}. Extra info: {data.get('extra_info') or 'none'}. "
        "Confirm? (yes/no, or 'cancel' to stop)"
    )
    answer = interrupt(summary)
    if is_cancel(answer):
        return cancelled_command("Okay, I've cancelled the operation.")
    if str(answer).strip().lower() in ("yes", "y", "confirm", "confirmed"):
        if state['remainder_data'].get('operation',None) == 'update':
            return Command(goto="update_remainder", update={"tool_response": "confirmed"})
        return Command(goto="create_remainder", update={"tool_response": "confirmed"})
    return Command(goto="ask_correction", update={"tool_response": "not_confirmed"})


def ask_correction(state: State):
    """Asks which field to correct after a rejected confirmation.

    Returns:
        Command: Updates 'remainder_data' and routes to the relevant check_* node.
    """
    answer = interrupt("What would you like to change — time, course, or the extra details? (or 'cancel' to stop)")
    if is_cancel(answer):
        return cancelled_command("Okay, I've cancelled the operation.")

    data = state['remainder_data']
    text = str(answer).strip().lower()
    if "time" in text:
        data['remainder_time'] = None
        target = "check_time"
    elif "course" in text:
        data['course_name'] = None
        target = "check_course"
    elif "extra" in text or "detail" in text or "event" in text:
        data['event_type'] = None
        data['extra_info'] = None
        target = "check_extra"
    else:
        data['remainder_time'] = None
        target = "check_time"
    return Command(goto=target, update={"remainder_data": data})


def create_remainder(state: State):
    remainder = Remainder(
        remainder_time=state['remainder_data']['remainder_time'],
        course_name=state['remainder_data']['course_name'],
        event_type=state['remainder_data']['event_type'],
        extra_info=state['remainder_data']['extra_info'],
        user_id=state['user_id']
    )
    with session() as db:
        course_name = remainder.course_name
        remainder_time = remainder.remainder_time
        if db.query(Remainder).filter(
            Remainder.course_name == course_name,
            Remainder.remainder_time == remainder_time
        ).first():
            return {'tool_response': f'Remainder already created for {course_name} at {remainder_time.strftime('%d %B %Y at %I:%M %p')}'}

        db.add(remainder)
        db.commit()
        schedule_remainder(remainder)
        course_name = remainder.course_name
        remainder_time = remainder.remainder_time

    return {'tool_response': f'Remainder created successfully for {course_name} at {remainder_time.strftime('%d %B %Y at %I:%M %p')}'}