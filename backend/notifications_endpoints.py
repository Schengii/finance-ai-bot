from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.notifications import save_subscription, send_push_notification
from backend.dependencies import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

class SubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict

@router.post("/subscribe")
async def subscribe(request: SubscriptionRequest, user: dict = Depends(get_current_user)):
    # Assuming user dict contains 'id'
    user_id = user.get('id')
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    subscription_info = {"endpoint": request.endpoint, "keys": request.keys}
    save_subscription(user_id, subscription_info)
    return {"status": "subscribed"}

class PushRequest(BaseModel):
    title: str
    body: str
    url: str = ""

@router.post("/send")
async def send_notification(push: PushRequest, user: dict = Depends(get_current_user)):
    user_id = user.get('id')
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    success = send_push_notification(user_id, push.title, push.body, push.url)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"status": "sent"}
