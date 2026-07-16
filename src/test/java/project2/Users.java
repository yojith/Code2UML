import java.util.ArrayList;
import java.util.List;

class User extends Entity implements Repository {
    static class Settings {
        public boolean notifications;
        public Settings(boolean notifications) { this.notifications = notifications; }
    }

    private Profile profile = new Profile("");
    private Address address;
    private Settings settings = new Settings(true);
    private AuditLog audit = new AuditLog();

    public User(String id, Address address) {
        super(id);
        this.address = address;
    }

    public String key() { return id; }
    public void save(Entity entity) { audit.record(entity.key()); }
    public Entity find(String key) { return this; }
}

class Team {
    private Repository repository;
    private List<User> members = new ArrayList<User>();
    private AuditLog audit = new AuditLog();

    public Team(Repository repository) { this.repository = repository; }
    public void add(User user) { members.add(user); }
    public Profile primaryProfile(User user) { return null; }
}
