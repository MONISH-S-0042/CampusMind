
from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from app.db.database import session
load_dotenv()
from app.services.utilities.time import to_local_time
def get_remainders(state:State):
    with session() as db:
        remainders = db.query(Remainder).filter(Remainder.user_id == state['user_id'], Remainder.is_active==True)
        if state['remainder_data'].get('course_name'):
            remainders = remainders.filter(Remainder.course_name == state['remainder_data'].get('course_name'))
        
        remainders = remainders.order_by(Remainder.remainder_time).all()
        res = [f"{r.event_type or 'Remainder'} for {r.course_name} at {to_local_time(r.remainder_time).strftime("%d %B %Y at %I:%M %p")}\n"
               + f"({r.extra_info if r.extra_info else ""})"
               for r in remainders]
        
    res = "Here are your reminders:\n" + "\n".join(res) if len(res)>0 else "No remainders added"
    return {'tool_response':res}