from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GenerationStatus(str, Enum):
    """На якому кроці зараз сесія генерації."""

    AWAITING_RESTRICTIONS = "awaiting_restrictions"
    AWAITING_PRODUCTS = "awaiting_products"
    SUGGESTIONS_READY = "suggestions_ready"


@dataclass
class GenerationSuggestion:
    """Короткий варіант рецепта, збережений у сесії."""

    title: str
    description: str
    cooking_time: int
    used_product_ids: list[int]


@dataclass
class GenerationSession:
    """Один "прохід" створення рецепта: обмеження -> продукти -> варіанти."""

    user_id: UUID
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)

    # Крок 1. "Обмежень немає" = restrictions_selected=True та порожній
    # restriction_ids. Поки користувач нічого не обрав — restrictions_selected=False.
    restrictions_selected: bool = False
    restriction_ids: list[int] = field(default_factory=list)

    # Кроки 2-3. Продукти, за якими згенеровані варіанти, та самі варіанти.
    product_ids: list[int] = field(default_factory=list)
    suggestions: list[GenerationSuggestion] = field(default_factory=list)

    # Збільшується при кожній зміні обмежень (захист від "застарілих" відповідей ШІ).
    revision: int = 0

    @classmethod
    def start(cls, user_id: UUID, ttl_minutes: int) -> "GenerationSession":
        return cls(
            user_id=user_id,
            expires_at=_utcnow() + timedelta(minutes=ttl_minutes),
        )

    @property
    def status(self) -> GenerationStatus:
        if not self.restrictions_selected:
            return GenerationStatus.AWAITING_RESTRICTIONS

        if not self.suggestions:
            return GenerationStatus.AWAITING_PRODUCTS

        return GenerationStatus.SUGGESTIONS_READY

    def is_expired(self) -> bool:
        return self.expires_at <= _utcnow()

    def touch(self, ttl_minutes: int) -> None:
        self.expires_at = _utcnow() + timedelta(minutes=ttl_minutes)

    def select_restrictions(self, restriction_ids: list[int]) -> None:
        """Зберігає обмеження та скидає все, що від них залежало."""
        self.restriction_ids = list(restriction_ids)
        self.restrictions_selected = True
        self.product_ids = []
        self.suggestions = []
        self.revision += 1

    def set_suggestions(
        self,
        product_ids: list[int],
        suggestions: list[GenerationSuggestion],
    ) -> None:
        self.product_ids = list(product_ids)
        self.suggestions = list(suggestions)
