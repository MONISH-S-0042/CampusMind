from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from langgraph.types import Command, interrupt
from app.db.database import session
from app.services.utilities.cancel_remainder_operation import cancelled_command
from app.services.notification.scheduler import unschedule_remainder
load_dotenv()
    
def delete_remainder(state:State):
    ids = state['remainder_data'].get('delete_ids', None)
    if not ids:
        return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry"})
    with session() as db:
        remainders = db.query(Remainder).filter(Remainder.id.in_(ids), Remainder.user_id == state['user_id']).all()
        
        if not remainders:
            return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry (Remainder doesn't exist)"})
        lines = [
            f"- {r.event_type or ''} for {r.course_name} at {r.remainder_time.strftime('%d %B %Y at %I:%M %p')}"
            for r in remainders
        ]
        prompt = (f"Are you sure you want to delete the Remainders. \n"+"\n".join(lines))
        
    confirmation = interrupt(prompt)
    
    if str(confirmation).strip().lower() not in {'yes','yeah','confirm','y'}:
        return cancelled_command("Ok, the remainders are not deleted")
    prompt = ""
    with session() as db:
        remainders = db.query(Remainder).filter(Remainder.id.in_(ids), Remainder.user_id == state['user_id']).all()
        if not remainders:
            return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry (Remainder doesn't exist)"})
        for remainder in remainders:
            prompt = prompt + (f"Remainders for course {remainder.course_name} at "
                f"{remainder.remainder_time.strftime('%d %B %Y at %I:%M %p')}\n")
            unschedule_remainder(remainder)
            db.delete(remainder)
        try:
            db.commit()
            prompt = prompt+ f" are deleted successfully"
        except:
            db.rollback()
            return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry"})
    return Command(goto='remainder_end',update={'tool_response':prompt})
    