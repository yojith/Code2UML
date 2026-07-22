#include "work.h"

void audit_record(struct AuditLog *self, char *message) { ++self->entries; }
void task_reassign(struct Task *self, struct User *user) { self->assignee = user; }
void team_add(struct Team *self, struct User *user) { self->members[0] = user; }
void project_add_task(struct Project *self, struct Task *task) { self->tasks[0] = task; }
void project_archive(struct Project *self, struct Entity *repository) { self->base.id = repository->id; }
