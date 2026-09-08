from app.db.models import Remainder
from app.db.database import session

def send_remainder(remainder_id:int, notification_type:str):
    print(f"Sending {notification_type} remainder to {remainder_id}")
    
    with session() as db:
        remainder = db.query(Remainder).filter(Remainder.id == remainder_id, Remainder.is_active ==True).first()
        if not remainder:
            print("Remainder does not exist or inactive")
            return
    tries = 1
    is_success = False
    while tries <= 3:
        tries = tries+1
        response = send_notification(remainder,notification_type)
        if response.get("status",None) and response.get("status",None) == "success":
            is_success = True
            break
    if is_success:
        with session() as db:
            remainder = db.query(Remainder).filter(Remainder.id == remainder_id, Remainder.is_active ==True).first()
            if not remainder:
                print("Remainder does not exist or inactive")
                return
            remainder.status = f"{notification_type}_sent"
            if notification_type == 'at_time':
                remainder.is_active = False
            try:
                db.commit()
                db.refresh(remainder)
            except:
                print(f"Failed to update status of {remainder.id}")
    
    
        
def send_notification(remainder:Remainder, notification_type:str):
    return {
        "status":"success"
    }        