from app.db.models import Remainder, User
from app.db.database import session
import os
import requests
from dotenv import load_dotenv
load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
BREVO_URL = os.getenv("BREVO_URL")

def send_remainder(remainder_id:int, notification_type:str):
    
    with session() as db:
        remainder = db.query(Remainder).filter(Remainder.id == remainder_id, Remainder.is_active ==True).first()
        if not remainder:
            print("Remainder does not exist or inactive")
            return
        user = db.query(User).filter(User.id == remainder.user_id).first()
        if not user or not user.email_id:
            print("No user or email for this remainder exist")
            return
        
    print(f"Sending {notification_type} remainder for remainder id: {remainder_id} to {user.email_id}")
    is_success = False
    for _ in range(3):
        response = send_notification(remainder,notification_type, user.email_id)
        if response.get("status",None) and response.get("status",None) == "success":
            is_success = True
            break
    status = f"{notification_type}_sent" if is_success else f"{notification_type}_failed"
    with session() as db:
        remainder = db.query(Remainder).filter(Remainder.id == remainder_id, Remainder.is_active ==True).first()
        if not remainder:
            print("Remainder does not exist or inactive")
            return
        remainder.status = status
        if notification_type == 'at_time' and is_success:
            remainder.is_active = False
        try:
            db.commit()
            db.refresh(remainder)
        except:
            db.rollback()
            print(f"Failed to update status of {remainder.id}")
    
    
    
def build_email_body(remainder: Remainder, notification_type: str):
    time_str = remainder.remainder_time.strftime('%d %B %Y at %I:%M %p')
    if notification_type == "before_1_day":
        label = "Reminder — 1 Day Remaining"
        
    elif notification_type == "before_2_hours":
        label = "Reminder — 2 Hours Remaining"
        
    elif notification_type == "at_time":
        label = "It's Time!"
        
    else:
        label = "Reminder"

    body = f"""
    <html>
        <body>
            <h2>{label}</h2>
            <p>
                <strong>Course:</strong>
                <strong style = "color:red">{remainder.course_name}</strong>
            </p>

            <p>
                <strong>Time:</strong>
                <strong>{time_str}</strong>
            </p>
    """
    if remainder.event_type:
        body+= f"""
            <p>
                <strong>Event:</strong>
                {remainder.event_type or 'Reminder'}
            </p>"""
    
    if remainder.extra_info:
        body += f"""
            <p>
                <strong>Note:</strong>
                {remainder.extra_info}
            </p>
        """

    body += """
        </body>
    </html>
    """

    return body
    

def send_notification(remainder: Remainder, notification_type: str, to_email: str):
    payload = {
        "sender": {"name": "CampusMind", "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": f"CampusMind Reminder: {remainder.course_name}",
        "htmlContent": build_email_body(remainder, notification_type),
    }
    try:
        response = requests.post(
            BREVO_URL,
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "accept": "application/json"},
            json=payload,
            timeout=10
        )
        if response.status_code == 201:
            print(f"Remainder sent for remainder id: {remainder.id}")
            return {"status": "success", "id": response.json().get("messageId")}
        print(f"Brevo error sending to {to_email}: {response.status_code} {response.text}")
        return {"status": "failed", "error": response.text}
    
    except requests.RequestException as e:
        print(f"Brevo request failed for {to_email}: {e}")
        return {"status": "failed", "error": str(e)}