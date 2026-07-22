from core import Address, AuditLog, Entity, Profile, Repository


class User(Entity, Repository):
    class Settings:
        def __init__(self, notifications: bool):
            self.notifications: bool = notifications

    def __init__(self, entity_id: str, address: Address):
        super().__init__(entity_id)
        self.profile: Profile = Profile("")
        self.address: Address = address
        self.settings: Settings = self.Settings(True)
        self.audit: AuditLog = AuditLog()

    def key(self) -> str:
        return self.entity_id

    def save(self, entity: Entity) -> None:
        self.audit.record(entity.key())

    def find(self, key: str) -> Entity:
        return self


class Team:
    def __init__(self, repository: Repository):
        self.repository: Repository = repository
        self.members: list[User] = []
        self.audit: AuditLog = AuditLog()

    def add(self, user: User) -> None:
        self.members.append(user)

    def primary_profile(self, user: User) -> Profile:
        return user.profile
