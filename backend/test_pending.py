from app.database import SessionLocal
from app.models import PendingAction

db = SessionLocal()

actions = db.query(PendingAction).filter(
    PendingAction.id == 7
).all()

for action in actions:
    print("ID:", action.id)
    print("USER:", action.user_id)
    print("TYPE:", action.action_type)
    print("STATUS:", action.status)
    print("DATA:", action.action_data)

db.close()