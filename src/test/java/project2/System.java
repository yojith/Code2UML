interface Repository { void save(Entity entity); }

abstract class Entity { public abstract String key(); }

class Profile {}

class User extends Entity implements Repository {
    class Settings {}
    private Profile profile = new Profile();
    private Settings settings = new Settings();
    public String key() { return "user"; }
    public void save(Entity entity) {}
}

class Team {
    private java.util.List<User> members;
    public void add(User user) { members.add(user); }
    public void persist(Repository repository) { Profile audit = new Profile(); }
}
