#include "collaboration.hpp"

void AuditLog::record(const std::string& message) { ++entries; }
User::User(Address* address) : address(address) {}
std::string User::key() { return id; }
void User::save(Entity* entity) { audit.record(entity->key()); }
Entity* User::find(const std::string& key) { return this; }

Team::Team(Repository* repository) : repository(repository) {}
void Team::add(User* user) { members.push_back(user); }
Profile* Team::primary_profile(User* user) { return nullptr; }

Task::Task(User* assignee) : assignee(assignee) {}
std::string Task::key() { return id; }
void Task::reassign(User* user) { assignee = user; }

Project::Project(User* owner, Team* team) : owner(owner), team(team) {}
std::string Project::key() { return id; }
void Project::add_task(Task* task) { tasks.push_back(task); }
void Project::archive(Repository* repository) { repository->save(this); }
