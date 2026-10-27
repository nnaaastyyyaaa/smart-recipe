class DomainError(Exception):
    """Базова помилка доменного рівня."""


class EmailAlreadyExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Користувач із таким email уже існує.")


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Невірний email або пароль.")