from datetime import datetime

from langgraph.types import Command, interrupt
from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from app.db.database import session
load_dotenv() 
import dateparser

def check_time(state: State):
    """Checks the time field before creating a remainder
    
        Returns:
            dict: Updates 'remainder_data'
        """
    if state['remainder_data'].get('remainder_time') is None:
        answer = interrupt("What time should this reminder be set for?")
        parsed = dateparser.parse(
            answer,
            settings={'RELATIVE_BASE': datetime.now(), 'PREFER_DATES_FROM': 'future'}
        )
        if parsed is None:
            # Couldn't understand it — ask again instead of storing garbage
            return Command(goto="check_time")
        state['remainder_data']['remainder_time'] = parsed
    return {"remainder_data": state['remainder_data']}

def check_course(state: State):
    """Checks the course field before creating a remainder

    Returns:
        dict: Updates 'remainder_data'
    """
    if not state['remainder_data'].get('course_name'):
        new_course = interrupt("Which course is this remainder for?")
        state['remainder_data']['course_name'] = new_course
    return {"remainder_data": state['remainder_data']}

def check_extra(state: State):
    """Asks/checks for extra data before creating a remainder

    Returns:
        dict: Updates 'remainder_data'
    """
    if not state['remainder_data'].get('event_type') and not state['remainder_data'].get('extra_info'):
        answer = interrupt(
            "Any additional details for this remainder — event type (quiz/assignment/etc.) "
            "or extra notes? Say 'skip' if none."
        )
        if str(answer).strip().lower() not in ("skip", "no", "none", ""):
            state['remainder_data']['extra_info'] = answer
    return {"remainder_data": state['remainder_data']}

def confirm_remainder(state: State):
    """Confirmation before creating a remainder

    Returns:
        dict: Updates 'remainder_data'
    """ 
    data = state['remainder_data']
    summary = (
        f"Please confirm: {data.get('event_type') or 'remainder'} for {data['course_name']} "
        f"at {data['remainder_time']}. Extra info: {data.get('extra_info') or 'none'}. Confirm? (yes/no)"
    )
    answer = interrupt(summary)
    if str(answer).strip().lower() in ("yes", "y", "confirm", "confirmed"):
        return {"tool_response": "confirmed"}
    return {"tool_response": "not_confirmed"}

def ask_correction(state: State):
    answer = interrupt("What would you like to change — time, course, or the extra details?")
    text = str(answer).strip().lower()
    if "time" in text:
        state['remainder_data']['remainder_time'] = None
        target = "check_time"
    elif "course" in text:
        state['remainder_data']['course_name'] = None
        target = "check_course"
    elif "extra" in text or "detail" in text or "event" in text:
        state['remainder_data']['event_type'] = None
        state['remainder_data']['extra_info'] = None
        target = "check_extra"
    else:
        # Unclear answer — safest fallback is to restart from the top of the chain
        state['remainder_data']['remainder_time'] = None
        target = "check_time"
    return {"remainder_data": state['remainder_data'], "tool_response": target}

def create_remainder(state:State):
    remainder = Remainder(
        remainder_time = state['remainder_data']['remainder_time'],
        course_name = state['remainder_data']['course_name'],
        is_active = True,
        event_type = state['remainder_data']['event_type'],
        extra_info = state['remainder_data']['extra_info'],
        user_id = state['user_id']
    )
    with session() as db:
        course_name = remainder.course_name
        remainder_time = remainder.remainder_time
        if db.query(Remainder).filter(
            Remainder.course_name == course_name,
            Remainder.remainder_time == remainder_time
        ).first():
            return {'tool_response':f'Remainder Already created {course_name} at {remainder_time}'}
            
        db.add(remainder)
        db.commit()
        course_name = remainder.course_name
        remainder_time = remainder.remainder_time
    
    return {'tool_response':f'Remainder created successfully for {course_name} at {remainder_time}'}

def route_after_correction(state: State):
    return state['tool_response']