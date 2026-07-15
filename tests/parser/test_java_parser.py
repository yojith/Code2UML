from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import ClassKind, ProjectLanguage, RelationshipType
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.java_parser import JavaParser


def write_source(tmp_path, name, source):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def class_by_name(module, name):
    return next(normalized_class for normalized_class in module.classes if normalized_class.name == name)


def assignment(normalized_class, member_name, ownership):
    return next(item for item in normalized_class.member_assignments if item.member_name == member_name and item.ownership == ownership)


def test_java_parser_normalizes_declarations_and_relationship_evidence(tmp_path):
    source = write_source(
        tmp_path,
        "OrderService.java",
        """
package example.orders;

import java.util.ArrayList;
import java.util.List;

@Deprecated
interface Repository<T> {
    T find(String key);
}

interface SpecialRepository extends Repository<Order> {}

abstract class BaseService {
    protected abstract void validate();
}

class Order {}
class Cache {}

public class OrderService extends BaseService implements Repository<Order> {
    private final Repository<Order> repository;
    private Cache cache;
    private List<Order> orders;
    public static int instances;

    public OrderService(Repository<Order> repository) {
        this.repository = repository;
        this.cache = new Cache();
        this.orders = new ArrayList<Order>();
    }

    @Override
    public Order find(String key) {
        Cache temporary = new Cache();
        return null;
    }

    public void store(List<Order> batch, Order order) {
        this.orders.add(order);
    }

    protected void validate() {}

    class State {}
}
""",
    )

    module = JavaParser().parse(str(source))[0]

    repository = class_by_name(module, "Repository")
    special_repository = class_by_name(module, "SpecialRepository")
    base_service = class_by_name(module, "BaseService")
    service = class_by_name(module, "OrderService")
    assert repository.kind is ClassKind.INTERFACE
    assert repository.methods[0].return_type == "T"
    assert special_repository.bases == ["Repository"]
    assert base_service.kind is ClassKind.ABSTRACT_CLASS
    assert base_service.methods[0].is_abstract
    assert service.bases == ["BaseService", "Repository"]
    assert class_by_name(module, "State").parent == "OrderService"
    assert [(attribute.name, attribute.type_name, attribute.visibility, attribute.is_static) for attribute in service.attributes] == [
        ("repository", "Repository<Order>", "-", False),
        ("cache", "Cache", "-", False),
        ("orders", "List<Order>", "-", False),
        ("instances", "int", "+", True),
    ]
    constructor = next(method for method in service.methods if method.is_constructor)
    assert [(parameter.name, parameter.type_name) for parameter in constructor.parameters] == [("repository", "Repository<Order>")]
    assert assignment(service, "repository", "supplied").type_name == "Repository"
    assert assignment(service, "cache", "constructed").type_name == "Cache"
    assert assignment(service, "orders", "constructed").type_name == "ArrayList<Order>"
    find = next(method for method in service.methods if method.name == "find")
    assert find.return_type == "Order"
    assert find.local_instantiations[0].class_name == "Cache"
    store = next(method for method in service.methods if method.name == "store")
    assert [(parameter.name, parameter.type_name) for parameter in store.parameters] == [("batch", "List<Order>"), ("order", "Order")]
    assert store.append_calls[0].collection_attribute == "orders"
    assert store.append_calls[0].item_name == "order"

    diagram = ClassAnalyzer().analyze([module])
    RelationshipAnalyzer().analyze([module], diagram)
    relationships = {(item.source, item.target, item.relationship_type) for item in diagram.relationships}
    assert ("OrderService", "Repository", RelationshipType.IMPLEMENTATION) in relationships
    assert ("OrderService", "Repository", RelationshipType.AGGREGATION) in relationships
    assert ("OrderService", "Cache", RelationshipType.COMPOSITION) in relationships
    assert ("OrderService", "Order", RelationshipType.AGGREGATION) in relationships


def test_java_parser_keeps_valid_declarations_and_reports_malformed_regions(tmp_path):
    source = write_source(
        tmp_path,
        "Broken.java",
        "class Before {}\nclass Broken { void run( { }\nclass After {}\n",
    )

    module = JavaParser().parse(str(source))[0]

    assert {normalized_class.name for normalized_class in module.classes} >= {"Before", "After"}
    assert module.diagnostics
    assert all(diagnostic.path == str(source) for diagnostic in module.diagnostics)
    assert all(diagnostic.line > 0 and diagnostic.column > 0 for diagnostic in module.diagnostics)
    assert all(diagnostic.severity == "error" and diagnostic.message for diagnostic in module.diagnostics)


def test_dispatcher_registers_the_java_adapter(tmp_path):
    source = write_source(tmp_path, "Model.java", "class Model {}\n")

    modules = AbstractSyntaxTreeLoader().load(ProjectLanguage.JAVA, str(source))

    assert modules[0].classes[0].name == "Model"
