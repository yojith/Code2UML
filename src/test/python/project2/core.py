from abc import ABC, abstractmethod
from typing import Protocol


class Entity(ABC):
    def __init__(self, entity_id: str):
        self.entity_id: str = entity_id

    @abstractmethod
    def key(self) -> str: ...


class Repository(Protocol):
    def save(self, entity: "Entity") -> None: ...

    def find(self, key: str) -> "Entity": ...


class Profile:
    def __init__(self, bio: str):
        self.bio: str = bio


class Address:
    def __init__(self, city: str):
        self.city: str = city


class AuditLog:
    def __init__(self):
        self.entries: list[str] = []

    def record(self, message: str) -> None:
        self.entries.append(message)
