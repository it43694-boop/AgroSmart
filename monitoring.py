import os
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, multiprocess, generate_latest
from contextlib import contextmanager
import structlog
import time

logger = structlog.get_logger()

registry = CollectorRegistry()

if os.getenv('PROMETHEUS_MULTIPROC_DIR'):
    multiprocess.MultiProcessCollector(registry)

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    registry=registry
)

db_connection_pool = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    ['pool'],
    registry=registry
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_name'],
    registry=registry
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_name'],
    registry=registry
)

ml_predictions = Counter(
    'ml_predictions_total',
    'Total ML predictions',
    ['model', 'status'],
    registry=registry
)

def track_request(method: str, endpoint: str, status: int):
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()

def track_request_duration(method: str, endpoint: str, duration: float):
    http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

@contextmanager
def track_db_operation(operation: str, table: str = 'unknown'):
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        db_query_duration.labels(operation=operation, table=table).observe(duration)

def track_cache_hit(cache_name: str):
    cache_hits.labels(cache_name=cache_name).inc()

def track_cache_miss(cache_name: str):
    cache_misses.labels(cache_name=cache_name).inc()

def track_ml_prediction(model: str, status: str = 'success'):
    ml_predictions.labels(model=model, status=status).inc()
