from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from services.push_notification_service import push_notification_service
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["notifications"])

class NotificationRequest(BaseModel):
    token: str
    title: str
    body: str
    data: dict = None

class MulticastNotificationRequest(BaseModel):
    tokens: list[str]
    title: str
    body: str
    data: dict = None

class TopicNotificationRequest(BaseModel):
    topic: str
    title: str
    body: str
    data: dict = None

class TopicSubscriptionRequest(BaseModel):
    tokens: list[str]
    topic: str

@router.post("/notifications/send")
async def send_notification(request: NotificationRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.send_notification(
        request.token, request.title, request.body, request.data
    )
    return result

@router.post("/notifications/multicast")
async def send_multicast_notification(request: MulticastNotificationRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.send_multicast_notification(
        request.tokens, request.title, request.body, request.data
    )
    return result

@router.post("/notifications/topic")
async def send_to_topic(request: TopicNotificationRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.send_to_topic(
        request.topic, request.title, request.body, request.data
    )
    return result

@router.post("/notifications/subscribe")
async def subscribe_to_topic(request: TopicSubscriptionRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.subscribe_to_topic(request.tokens, request.topic)
    return result

@router.post("/notifications/unsubscribe")
async def unsubscribe_from_topic(request: TopicSubscriptionRequest, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.unsubscribe_from_topic(request.tokens, request.topic)
    return result

@router.post("/notifications/order/{order_id}")
async def send_order_notification(order_id: int, status: str, token: str, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.send_order_notification(token, order_id, status)
    return result

@router.post("/notifications/weather-alert")
async def send_weather_alert(region: str, alert_type: str, token: str, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.send_weather_alert(token, region, alert_type)
    return result

@router.post("/notifications/loan/{loan_id}")
async def send_loan_notification(loan_id: int, status: str, token: str, current_user: models.User = Depends(auth.get_current_user)):
    result = await push_notification_service.send_loan_notification(token, loan_id, status)
    return result
