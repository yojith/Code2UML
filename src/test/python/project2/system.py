from abc import ABC, abstractmethod
from typing import Protocol


class Repository(Protocol):
    def save(self, entity: "Entity") -> None: ...


class Entity(ABC):
    @abstractmethod
    def key(self) -> str: ...


class Profile:
    pass


class User(Entity, Repository):
    class Settings:
        pass

    def __init__(self):
        self.profile = Profile()
        self.settings = self.Settings()

    def key(self) -> str:
        return "user"


class Team:
    def __init__(self):
        self.members: list[User] = []

    def add(self, user: User) -> None:
        self.members.append(user)

    def persist(self, repository: Repository) -> None:
        audit = Profile()
