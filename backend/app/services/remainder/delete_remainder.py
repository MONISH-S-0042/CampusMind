from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from langgraph.types import Command, interrupt
from app.db.database import session
from app.services.utilities.cancel_remainder_operation import cancelled_command
load_dotenv()
    
def delete_remainder(state:State):
    id = state['remainder_data'].get('delete_id', None)
    if not id:
        return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry"})
    with session() as db:
        remainder = db.query(Remainder).filter(Remainder.id == id, Remainder.user_id == state['user_id']).first()
        
        if not remainder:
            return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry (Remainder doesn't exist)"})

        prompt = (f"Are you sure you want to delete the {remainder.event_type if remainder.event_type else ''} "
                f"Remainder for course {remainder.course_name} at {remainder.remainder_time.strftime('%d %B %Y at %I:%M %p')}")
    confirmation = interrupt(prompt)
    
    if str(confirmation).strip().lower() not in {'yes','yeah','confirm','y'}:
        return cancelled_command("Ok, the remainder is not deleted")
    
    with session() as db:
        remainder = db.query(Remainder).filter(Remainder.id == id, Remainder.user_id == state['user_id']).first()
        if not remainder:
            return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry (Remainder doesn't exist)"})
        db.delete(remainder)
        prompt = (f"Remainder for course {remainder.course_name} at "
            f"{remainder.remainder_time.strftime('%d %B %Y at %I:%M %p')}")
        try:
            db.commit()
            prompt = prompt+ f" is deleted successfully"
        except:
            db.rollback()
            return Command(goto='remainder_end',update={'tool_response':"An error occured, Kindly retry"})
    return Command(goto='remainder_end',update={'tool_response':prompt})
    