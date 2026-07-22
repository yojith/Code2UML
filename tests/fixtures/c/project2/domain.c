#include "domain.h"

int user_key(struct User *self) { return self->base.id; }
void user_move(struct User *self, struct Address *address) { self->address = address; }
struct Profile *user_profile(struct User *self) { return &self->profile; }
