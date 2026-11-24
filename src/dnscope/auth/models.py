from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


@dataclass(frozen=True)
class ApiKeyContext:
    key_id: UUID
    role: Role
    name: str


class AuthError(Exception):
    """Raised on authentication or authorization failure."""

    def __init__(self, status_code: int, error: str) -> None:
        super().__init__(error)
        self.status_code = status_code
        self.error = error
