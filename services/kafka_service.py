"""Kafka Event Bus - Base de tous les modules"""
import json
import logging
from typing import Dict, Any, Callable, List
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092").split(",")

# Try importing Kafka, fallback to mock if not available
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False
    logger.warning("⚠️ Kafka non disponible - Mode événements simulé")
    KafkaProducer = None
    KafkaConsumer = None
    KafkaError = None

# Event types
class EventType:
    LISTING_CREATED = "listing_created"
    ORDER_PLACED = "order_placed"
    PAYMENT_CONFIRMED = "payment_confirmed"
    CREDIT_SCORE_COMPUTED = "credit_score_computed"
    FRAUD_ALERT = "fraud_alert"
    YIELD_PREDICTION_READY = "yield_prediction_ready"
    INSURANCE_TRIGGERED = "insurance_triggered"
    TOKEN_MINTED = "token_minted"
    TRACEABILITY_RECORDED = "traceability_recorded"
    CARBON_CALCULATED = "carbon_calculated"
    REPUTATION_UPDATED = "reputation_updated"
    BADGE_EARNED = "badge_earned"
    EXPORT_DOCUMENT_READY = "export_document_ready"
    PROPOSAL_CREATED = "proposal_created"
    VOTE_CAST = "vote_cast"
    FUNDS_DISTRIBUTED = "funds_distributed"

class KafkaEventProducer:
    """Produire des events dans Kafka ou en fallback mode"""

    def __init__(self):
        self.producer = None
        self.use_fallback = not HAS_KAFKA
        
        if not self.use_fallback:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BROKERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    retries=3,
                    acks="all"
                )
                logger.info("✓ Kafka Producer initialized")
            except Exception as e:
                logger.warning(f"Kafka Producer failed: {e} - Using fallback mode")
                self.use_fallback = True
                self.producer = None
        
        if self.use_fallback:
            logger.info("[fallback] Events stored in memory queue")
            self._event_queue = []

    def publish(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publier un événement"""
        try:
            event = {
                "event_type": event_type,
                "data": data,
                "timestamp": str(__import__("datetime").datetime.utcnow())
            }

            if self.use_fallback:
                # Mode fallback - store in memory queue
                self._event_queue.append(event)
                logger.debug(f"[fallback] Event queued: {event_type}")
                return True
            elif self.producer:
                future = self.producer.send(event_type, event)
                future.get(timeout=10)
                logger.info(f"✓ Event published: {event_type}")
                return True
            else:
                logger.warning(f"Producer unavailable, skipping event: {event_type}")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to publish event {event_type}: {e}")
            return False

    def close(self):
        if self.producer:
            try:
                self.producer.close()
            except Exception as e:
                logger.warning(f"Error closing producer: {e}")

class KafkaEventConsumer:
    """Consommer des events depuis Kafka ou en fallback mode (Worker asynchrone)"""

    def __init__(self, event_type: str, consumer_group: str):
        self.consumer = None
        self.use_fallback = not HAS_KAFKA
        self.event_type = event_type
        self.consumer_group = consumer_group
        
        if not self.use_fallback:
            try:
                self.consumer = KafkaConsumer(
                    event_type,
                    bootstrap_servers=KAFKA_BROKERS,
                    group_id=consumer_group,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="earliest",
                    enable_auto_commit=True
                )
                logger.info(f"✓ Kafka Consumer initialized for {event_type}")
            except Exception as e:
                logger.warning(f"Kafka Consumer failed for {event_type}: {e} - Using fallback")
                self.use_fallback = True
        
        if self.use_fallback:
            logger.info(f"[fallback] Consumer initialized for {event_type} (group: {consumer_group})")
            self._event_callbacks: Dict[str, List[Callable]] = {}

    def subscribe(self, event_types: List[str], callback: Callable):
        """S'abonner à des types d'événements"""
        if self.use_fallback:
            for et in event_types:
                if et not in self._event_callbacks:
                    self._event_callbacks[et] = []
                self._event_callbacks[et].append(callback)
            logger.debug(f"[fallback] Subscribed to {event_types}")
            return
        
        if self.consumer:
            try:
                self.consumer.subscribe(event_types)
                logger.info(f"Subscribed to: {event_types}")
            except Exception as e:
                logger.error(f"Failed to subscribe: {e}")

    def consume(self, callback: Callable = None, timeout_ms: int = 1000) -> None:
        """Consommer des événements"""
        if self.use_fallback:
            logger.debug("[fallback] No events to consume in fallback mode")
            return
        
        if not self.consumer:
            return

        try:
            for message in self.consumer:
                if callback:
                    callback(message.value)
        except Exception as e:
            logger.error(f"Error consuming events: {e}")

    def close(self):
        if self.consumer:
            try:
                self.consumer.close()
            except Exception as e:
                logger.warning(f"Error closing consumer: {e}")

    def listen(self, callback: Callable[[Dict], None]):
        """Écouter les événements et appeler callback"""
        if self.use_fallback:
            logger.debug("[fallback] No events to listen in fallback mode")
            return

        if not self.consumer:
            logger.error("Consumer not initialized")
            return

        try:
            for message in self.consumer:
                event = message.value
                logger.info(f"→ Event received: {event['event_type']}")
                callback(event)
        except Exception as e:
            logger.error(f"Consumer error: {e}")


# Singleton instances
producer = KafkaEventProducer()

def publish_event(event_type: str, data: Dict[str, Any]) -> bool:
    """Helper function pour publier des événements"""
    return producer.publish(event_type, data)
