import java.util.ArrayList;
import java.util.List;

class Task extends Entity {
    private User assignee;
    private AuditLog audit = new AuditLog();

    public Task(String id, User assignee) {
        super(id);
        this.assignee = assignee;
    }

    public String key() { return id; }
    public void reassign(User user) { this.assignee = user; }
}

class Project extends Entity {
    private User owner;
    private Team team;
    private List<Task> tasks = new ArrayList<Task>();

    public Project(String id, User owner, Team team) {
        super(id);
        this.owner = owner;
        this.team = team;
    }

    public String key() { return id; }
    public void addTask(Task task) { tasks.add(task); }
    public void archive(Repository repository) { repository.save(this); }
}
