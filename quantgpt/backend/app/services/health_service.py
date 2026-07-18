from sqlalchemy import text
from sqlalchemy.orm import Session


class HealthService:
    def check_db(self, db: Session) -> tuple[bool, str]:
        try:
            db.execute(text("SELECT 1"))
            return True, "postgres: ok"
        except Exception as e:
            return False, f"postgres: {e}"

    def check_redis(self, redis_url: str) -> tuple[bool, str]:
        try:
            import redis
            client = redis.from_url(redis_url, socket_connect_timeout=2)
            return bool(client.ping()), "redis: ok"
        except Exception as e:
            return False, f"redis: {e}"
