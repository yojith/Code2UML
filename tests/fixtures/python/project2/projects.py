from core import AuditLog, Entity, Repository
from users import Team, User


class Task(Entity):
    def __init__(self, entity_id: str, assignee: User):
        super().__init__(entity_id)
        self.assignee: User = assignee
        self.audit: AuditLog = AuditLog()

    def key(self) -> str:
        return self.entity_id

    def reassign(self, user: User) -> None:
        self.assignee = user


class Project(Entity):
    def __init__(self, entity_id: str, owner: User, team: Team):
        super().__init__(entity_id)
        self.owner: User = owner
        self.team: Team = team
        self.tasks: list[Task] = []

    def key(self) -> str:
        return self.entity_id

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def archive(self, repository: Repository) -> None:
        repository.save(self)
