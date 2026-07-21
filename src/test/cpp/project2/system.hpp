#pragma once

#include <string>

class Entity {
public:
    virtual std::string key() = 0;
protected:
    std::string id;
};

class Repository {
public:
    virtual void save(Entity* entity) = 0;
    virtual Entity* find(const std::string& key) = 0;
};

struct Profile {
    std::string bio;
};

struct Address {
    std::string city;
};

struct AuditLog {
    int entries;
    void record(const std::string& message);
};
