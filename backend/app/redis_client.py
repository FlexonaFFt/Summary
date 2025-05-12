import aioredis

redis = aioredis.from_url("redis://redis:6379", decode_responses=True)  # Изменено с redis://redis:6379 на redis://localhost:6379