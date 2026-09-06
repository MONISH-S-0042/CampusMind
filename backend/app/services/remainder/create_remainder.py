import re
from datetime import datetime, timezone

from langgraph.types import Command, interrupt
from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from app.db.database import session
load_dotenv()
import dateparser

CANCEL_PHRASES = {"cancel", "stop", "nevermind", "never mind", "quit", "exit", "abort", "cancel remainder"}


def is_cancel(answer) -> bool:
    return str(answer).strip().lower() in CANCEL_PHRASES


def cancelled_command():
    return Command(
        goto="chatbot",
        update={
            "tool_response": "Okay, I've cancelled the reminder — nothing was saved.",
            "remainder_data": {
                "operation": None, "course_name": None, "time_mentioned": None,
                "remainder_time": None, "event_type": None, "extra_info": None,
                "retry_message": None,
            },
        },
    )

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
    def to_aware_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def is_past_date(date):
        return to_aware_utc(date) <= datetime.now(timezone.utc)

    data = state['remainder_data']

    if data.get('remainder_time') is None or data.get('time_mentioned') is False:
        prompt = data.pop('retry_message', None) or "What time should this reminder be set for? (or 'cancel' to stop)"
        answer = interrupt(prompt)
        if is_cancel(answer):
            return cancelled_command()

        cleaned = clean_weekday_modifiers(str(answer))
        parsed = dateparser.parse(
            cleaned,
            settings={'RELATIVE_BASE': datetime.now(), 'PREFER_DATES_FROM': 'future'}
        )
        parsed = to_aware_utc(parsed) if parsed is not None else None
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
            return cancelled_command()
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
            return cancelled_command()
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
        f"at {data['remainder_time']}. Extra info: {data.get('extra_info') or 'none'}. "
        "Confirm? (yes/no, or 'cancel' to stop)"
    )
    answer = interrupt(summary)
    if is_cancel(answer):
        return cancelled_command()
    if str(answer).strip().lower() in ("yes", "y", "confirm", "confirmed"):
        return Command(goto="create_remainder", update={"tool_response": "confirmed"})
    return Command(goto="ask_correction", update={"tool_response": "not_confirmed"})


def ask_correction(state: State):
    """Asks which field to correct after a rejected confirmation.

    Returns:
        Command: Updates 'remainder_data' and routes to the relevant check_* node.
    """
    answer = interrupt("What would you like to change — time, course, or the extra details? (or 'cancel' to stop)")
    if is_cancel(answer):
        return cancelled_command()

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
        is_active=True,
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
            return {'tool_response': f'Remainder already created for {course_name} at {remainder_time}'}

        db.add(remainder)
        db.commit()
        course_name = remainder.course_name
        remainder_time = remainder.remainder_time

    return {'tool_response': f'Remainder created successfully for {course_name} at {remainder_time}'}