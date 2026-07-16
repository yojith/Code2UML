#pragma once

#include "domain.h"

#define TEAM_LIMIT 16
#define PROJECT_TASK_LIMIT 32

struct AuditLog { int entries; };
struct Task {
    struct Entity base;
    struct User *assignee;
    struct AuditLog audit;
};
struct Team {
    struct User *members[TEAM_LIMIT];
    struct AuditLog audit;
};
struct Project {
    struct Entity base;
    struct User *owner;
    struct Team *team;
    struct Task *tasks[PROJECT_TASK_LIMIT];
};

void audit_record(struct AuditLog *self, char *message);
void task_reassign(struct Task *self, struct User *user);
void team_add(struct Team *self, struct User *user);
void project_add_task(struct Project *self, struct Task *task);
void project_archive(struct Project *self, struct Entity *repository);
