#define MAX_TEAM_MEMBERS 32

struct Entity { int id; };
struct Profile { char bio[64]; };
struct User { struct Entity base; struct Profile profile; };
struct Team { struct User *members[MAX_TEAM_MEMBERS]; };

void team_add(struct Team *self, struct User *user);
void team_persist(struct Team *self, struct Entity *repository);
