#pragma once

#define PROFILE_LIMIT 64

struct Entity { int id; };
struct Profile { char *bio; };
struct Address { char *city; };
struct User {
    struct Entity base;
    struct Profile profile;
    struct Address *address;
    int notifications;
};

int user_key(struct User *self);
void user_move(struct User *self, struct Address *address);
struct Profile *user_profile(struct User *self);
