#include <vector>

class Entity {
public:
    virtual int key() = 0;
protected:
    int id;
};
class Repository { public: virtual void save(Entity* entity) = 0; };
struct Profile {};

class User : public Entity, public Repository {
public:
    struct Settings {};
    int key();
    void save(Entity* entity);
private:
    Profile profile;
    Settings settings;
};

class Team {
public:
    void add(User* user) { members.push_back(user); }
    void persist(Repository* repository) { Profile audit; }
private:
    std::vector<User*> members;
    User* lead;
};
