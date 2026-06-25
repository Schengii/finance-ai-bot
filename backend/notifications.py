import json
import logging
from typing import Dict, Any

import redis
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

# Redis client for storing subscriptions (simple example)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

SUBSCRIPTIONS_KEY = 'user_subscriptions'

def save_subscription(user_id: int, subscription_info: Dict[str, Any]):
    """Store a user's push subscription in Redis.

    Args:
        user_id: Identifier of the user.
        subscription_info: The subscription dict received from the client.
    """
    try:
        redis_client.hset(SUBSCRIPTIONS_KEY, user_id, json.dumps(subscription_info))
        logger.info(f"Saved subscription for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving subscription for user {user_id}: {e}")

def get_subscription(user_id: int) -> Dict[str, Any] | None:
    """Retrieve a stored subscription for a user.
    """
    try:
        data = redis_client.hget(SUBSCRIPTIONS_KEY, user_id)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Error retrieving subscription for user {user_id}: {e}")
    return None

def send_push_notification(user_id: int, title: str, body: str, url: str = ""):
    """Send a Web Push notification to a user.

    Requires VAPID keys to be configured in environment variables.
    """
    subscription = get_subscription(user_id)
    if not subscription:
        logger.warning(f"No subscription found for user {user_id}")
        return False

    vapid_private_key = "YOUR_VAPID_PRIVATE_KEY"
    vapid_claims = {
        "sub": "mailto:admin@example.com"
    }
    payload = json.dumps({"title": title, "body": body, "url": url})
    try:
        response = webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims,
        )
        logger.info(f"Push notification sent to user {user_id}, response: {response}")
        return True
    except WebPushException as ex:
        logger.error(f"Web push failed for user {user_id}: {ex}")
        return False
