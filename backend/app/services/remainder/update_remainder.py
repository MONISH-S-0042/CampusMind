from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.db.models import Remainder
from langgraph.types import Command, interrupt
from app.db.database import session
from app.services.utilities.cancel_remainder_operation import cancelled_command, is_cancel
load_dotenv()


def get_remainder_tochange(state:State):#Selects remainder for both delete and update
    data = []
    with session() as db:
        remainders = db.query(Remainder).filter(Remainder.user_id == state['user_id'])
        if state['remainder_data']['course_name']:
            remainders = remainders.filter(Remainder.course_name == state['remainder_data']['course_name'])
        if state['remainder_data']['event_type']:
            remainders = remainders.filter(Remainder.event_type == state['remainder_data']['event_type'])
        remainders = remainders.all()
        for i,r in enumerate(remainders):
            data.append(f" {i+1}. Remainder for {r.course_name} {r.event_type if r.event_type else ''} set at {r.remainder_time.strftime('%d %B %Y at %I:%M %p')}")
    if len(data)==0:
        return Command(goto='remainder_end', update={'tool_response':'No such remainders exists, try viewing all remainders'})
    if len(data)>1 or state['remainder_data'].get('course_name',None) is None:
        prompt = None
        if(state['remainder_data'].get('retry_message',None)):
            prompt = state['remainder_data'].pop('retry_message',None)
        prompt =prompt if prompt else (
                "Kindly enter the S.No of the remainder which you wish to select for this\n"
                f"{'\n'.join(data)}")
        selection = interrupt(prompt)
        if is_cancel(selection):
            return cancelled_command("Okay, I've cancelled the operation — nothing was updated.") 
        is_delete = state['remainder_data']['operation'] == 'delete'
        raw_parts = [p.strip() for p in str(selection).replace(',', ' ').split() if p.strip()]
        try:
            indices = [int(p) for p in raw_parts]
            if not is_delete and len(indices) > 1:
                raise ValueError("update only supports one selection")
            if any(i < 1 or i > len(data) for i in indices):
                raise ValueError("out of range")
        except ValueError:
            state['remainder_data']['retry_message']=(
                f"Kindly enter {'one or more values' if is_delete else 'a single value'} from 1 to {len(data)}\n" + "\n".join(data))
            return Command(goto='start_get_remainder',update={'remainder_data':state['remainder_data']})
    
    if state['remainder_data']['operation'] == 'delete':
        state['remainder_data']['delete_ids'] = [remainders[i - 1].id for i in indices]
        return Command(goto='delete_remainder',update={'remainder_data':state['remainder_data']})
    
    rem =  remainders[indices[0] - 1]
    state['remainder_data']['course_name'] =  rem.course_name
    state['remainder_data']['event_type'] =  rem.event_type
    state['remainder_data']['update_id'] = rem.id
    return Command(goto='check_time',update={'remainder_data':state['remainder_data']})

def update_remainder(state:State):
    id = state['remainder_data'].get('update_id', None)
    if not id:
        return {'tool_response':"An error occured, Kindly retry"}
    with session() as db:
        old_remainder = db.query(Remainder).filter(Remainder.id == id, Remainder.user_id == state['user_id']).first()
        
        if not old_remainder:
            return {'tool_response':"An error occured, Kindly retry (Remainder doesn't exist)"}
        
        prompt = f"Remainder for course updated from {old_remainder.course_name} at {old_remainder.remainder_time.strftime('%d %B %Y at %I:%M %p')}"
        old_remainder.course_name = state['remainder_data']['course_name'] or old_remainder.course_name
        old_remainder.remainder_time = state['remainder_data']['remainder_time'] or old_remainder.remainder_time
        old_remainder.event_type = state['remainder_data']['event_type'] or old_remainder.event_type
        old_remainder.extra_info = state['remainder_data']['extra_info'] or old_remainder.extra_info
        try:
            db.commit()
            db.refresh(old_remainder)
            prompt = prompt+ f" to {old_remainder.course_name} at {old_remainder.remainder_time.strftime('%d %B %Y at %I:%M %p')}"
        except:
            db.rollback()
            return {'tool_response':"An error occured, Kindly retry"}
    return {'tool_response':prompt}
    