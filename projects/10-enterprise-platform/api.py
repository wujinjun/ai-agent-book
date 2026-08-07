"""项目 10 FastAPI 入口。"""

import os
from pathlib import Path

from ai_agent_book.apps.enterprise_platform import (
    EnterprisePlatform,
    HMACIdentityVerifier,
    RedisRunQueue,
    create_enterprise_app,
)

database_url = os.getenv("DATABASE_URL")
queue = RedisRunQueue(os.environ["REDIS_URL"]) if os.getenv("REDIS_URL") else None
platform = EnterprisePlatform(
    database_url or Path(os.getenv("DATABASE_PATH", ".data/platform.db")),
    queue=queue,
)
platform.ensure_tenant("demo", "Demo Tenant")
platform.ensure_user("demo", "admin", role="admin")

signing_secret = os.getenv("AUTH_HMAC_SECRET")
verifier = HMACIdentityVerifier(signing_secret) if signing_secret else None
app = create_enterprise_app(platform, identity_verifier=verifier)
