import java.util.ArrayList;
import java.util.List;

abstract class Entity {
    protected String id;
    public Entity(String id) { this.id = id; }
    public abstract String key();
}

interface Repository {
    void save(Entity entity);
    Entity find(String key);
}

class Profile {
    public String bio;
    public Profile(String bio) { this.bio = bio; }
}

class Address {
    public String city;
    public Address(String city) { this.city = city; }
}

class AuditLog {
    private List<String> entries = new ArrayList<String>();
    public void record(String message) { entries.add(message); }
}
