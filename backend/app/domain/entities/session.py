from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class Session:
    token_hash: str
    user_id: UUID
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(timezone.utc)