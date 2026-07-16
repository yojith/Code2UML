#include "domain.h"

void team_add(struct Team *self, struct User *user) {
    self->members[0] = user;
}

void team_persist(struct Team *self, struct Entity *repository) {
    struct Profile audit;
}
