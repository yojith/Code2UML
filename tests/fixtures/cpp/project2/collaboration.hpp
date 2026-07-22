#pragma once

#include "system.hpp"
#include <vector>

class User : public Entity, public Repository {
public:
    struct Settings { bool notifications; };
    explicit User(Address* address);
    std::string key() override;
    void save(Entity* entity) override;
    Entity* find(const std::string& key) override;
private:
    Profile profile;
    Address* address;
    Settings settings;
    AuditLog audit;
};

class Team {
public:
    explicit Team(Repository* repository);
    void add(User* user);
    Profile* primary_profile(User* user);
private:
    Repository* repository;
    std::vector<User*> members;
    AuditLog audit;
};

class Task : public Entity {
public:
    explicit Task(User* assignee);
    std::string key() override;
    void reassign(User* user);
private:
    User* assignee;
    AuditLog audit;
};

class Project : public Entity {
public:
    Project(User* owner, Team* team);
    std::string key() override;
    void add_task(Task* task);
    void archive(Repository* repository);
private:
    User* owner;
    Team* team;
    std::vector<Task*> tasks;
};
