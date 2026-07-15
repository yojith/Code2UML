from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import ClassKind, ProjectLanguage, RelationshipType
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.cpp_parser import CppParser


def write_source(tmp_path, name, source):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def class_by_name(module, name):
    return next(normalized_class for normalized_class in module.classes if normalized_class.name == name)


def assignment(normalized_class, member_name, ownership):
    return next(item for item in normalized_class.member_assignments if item.member_name == member_name and item.ownership == ownership)


def test_cpp_parser_normalizes_declarations_and_relationship_evidence(tmp_path):
    source = write_source(
        tmp_path,
        "orders.cpp",
        r"""
namespace shop {
template <typename T>
class Repository {
public:
    virtual T find(const int& id) const = 0;
    virtual ~Repository() = default;
};

class BaseService {
protected:
    virtual void validate() = 0;
public:
    virtual ~BaseService() = 0;
};

BaseService::~BaseService() = default;

struct Address {};
class Customer {};
class Cache {};

class Order final : public BaseService, public Repository<Order> {
public:
    class Line {};
    Order(Address address, Customer& customer, Cache* cache);
    Order find(const int& id) const override;
    void save(Customer customer);
protected:
    void validate() override {}
private:
    Address address;
    Customer& customer;
    Cache* cache;
    static int instances;
};

Order::Order(Address address, Customer& customer, Cache* cache)
    : address(address), customer(customer), cache(cache) {}

Order Order::find(const int& id) const {
    Cache temporary;
    return Order(address, customer, cache);
}

void Order::save(Customer customer) {
    Customer copy{customer};
}
}
""",
    )

    module = CppParser().parse(str(source))[0]

    assert module.diagnostics == []
    assert [item.name for item in module.classes] == ["Repository", "BaseService", "Address", "Customer", "Cache", "Order", "Line"]
    repository = class_by_name(module, "Repository")
    base_service = class_by_name(module, "BaseService")
    order = class_by_name(module, "Order")
    assert repository.kind is ClassKind.INTERFACE
    assert repository.methods[0].return_type == "T"
    assert repository.methods[0].is_pure_virtual
    assert base_service.kind is ClassKind.ABSTRACT_CLASS
    assert order.bases == ["BaseService", "Repository"]
    assert class_by_name(module, "Line").parent == "Order"
    assert [(item.name, item.type_name, item.visibility, item.is_static) for item in order.attributes] == [
        ("address", "Address", "-", False),
        ("customer", "Customer&", "-", False),
        ("cache", "Cache*", "-", False),
        ("instances", "int", "-", True),
    ]
    assert assignment(order, "address", "value").type_name == "Address"
    assert assignment(order, "customer", "reference").type_name == "Customer"
    assert assignment(order, "cache", "reference").type_name == "Cache"
    constructor = next(item for item in order.methods if item.is_constructor)
    assert [(item.name, item.type_name) for item in constructor.parameters] == [("address", "Address"), ("customer", "Customer&"), ("cache", "Cache*")]
    assert assignment(order, "address", "supplied").type_name == "Address"
    find = next(item for item in order.methods if item.name == "find")
    assert find.return_type == "Order"
    assert [(item.name, item.type_name) for item in find.parameters] == [("id", "const int&")]
    assert [(item.class_name, item.assigned_name) for item in find.local_instantiations] == [("Cache", "temporary")]
    save = next(item for item in order.methods if item.name == "save")
    assert [(item.class_name, item.assigned_name) for item in save.local_instantiations] == [("Customer", "copy")]

    diagram = ClassAnalyzer().analyze([module])
    RelationshipAnalyzer().analyze([module], diagram)
    relationships = {(item.source, item.target, item.relationship_type) for item in diagram.relationships}
    assert ("Order", "Repository", RelationshipType.IMPLEMENTATION) in relationships
    assert ("Order", "BaseService", RelationshipType.INHERITANCE) in relationships
    assert ("Order", "Address", RelationshipType.COMPOSITION) in relationships
    assert ("Order", "Customer", RelationshipType.AGGREGATION) in relationships
    assert ("Order", "Cache", RelationshipType.AGGREGATION) in relationships


def test_cpp_interface_requires_public_pure_behavior_and_no_instance_state(tmp_path):
    source = write_source(
        tmp_path,
        "kinds.hpp",
        """
class Port {
public:
    virtual void send() = 0;
    virtual ~Port() = 0;
};

class StatefulPort {
public:
    virtual void send() = 0;
private:
    int state;
};

class HiddenPort {
protected:
    virtual void send() = 0;
};

class StaticPort {
public:
    virtual void send() = 0;
private:
    static int state;
};

class ConcreteDestructorPort {
public:
    virtual void send() = 0;
    virtual ~ConcreteDestructorPort() {}
};
""",
    )

    module = CppParser().parse(str(source))[0]

    assert class_by_name(module, "Port").kind is ClassKind.INTERFACE
    assert class_by_name(module, "StatefulPort").kind is ClassKind.ABSTRACT_CLASS
    assert class_by_name(module, "HiddenPort").kind is ClassKind.ABSTRACT_CLASS
    assert class_by_name(module, "StaticPort").kind is ClassKind.INTERFACE
    assert class_by_name(module, "ConcreteDestructorPort").kind is ClassKind.ABSTRACT_CLASS


def test_cpp_parser_recovers_diagnostics_and_dispatcher_registers_adapter(tmp_path):
    broken = write_source(tmp_path, "broken.cpp", "class Before {};\nclass Broken { void run( ; };\nclass After {};\n")

    module = AbstractSyntaxTreeLoader().load(ProjectLanguage.CPP, str(broken))[0]

    assert {item.name for item in module.classes} >= {"Before", "After"}
    assert module.diagnostics
    assert all(item.path == str(broken) and item.line > 0 and item.column > 0 for item in module.diagnostics)


def test_cpp_parser_links_headers_definitions_overloads_and_initializer_evidence(tmp_path):
    header = write_source(
        tmp_path,
        "models.hpp",
        """
class Foo {};

class Port {
public:
    virtual void send() = 0;
    virtual ~Port();
};

class InlineOwner {
public:
    InlineOwner(Foo* supplied) : supplied_(supplied), created_(new Foo()), value_(Foo{}), empty_() {}
private:
    Foo* supplied_;
    Foo* created_;
    Foo value_;
    Foo empty_;
};

class Owner {
public:
    Owner(Foo* supplied);
    Owner(int count);
    Owner(float ratio);
    Foo* get();
    Foo& ref();
private:
    Foo* supplied_;
    Foo* created_;
    Foo value_;
    Foo empty_;
};
""",
    )
    implementation = write_source(
        tmp_path,
        "models.cpp",
        """
Owner::Owner(Foo* supplied)
    : supplied_(supplied), created_(new Foo()), value_(Foo{}), empty_() {}

Owner::Owner(int count) {
    Foo integer_local;
}

Owner::Owner(float ratio) {
    Foo float_local;
    Foo another_float_local;
}

Foo* Owner::get() { return created_; }
Foo& Owner::ref() { return value_; }
Port::~Port() {}
""",
    )

    modules = CppParser().parse(str(header), str(implementation))
    owner = class_by_name(modules[0], "Owner")
    inline = class_by_name(modules[0], "InlineOwner")

    assert class_by_name(modules[0], "Port").kind is ClassKind.ABSTRACT_CLASS
    assert {(method.name, method.return_type) for method in owner.methods if method.name in {"get", "ref"}} == {("get", "Foo*"), ("ref", "Foo&")}
    constructors = {method.parameters[0].type_name: method for method in owner.methods if method.is_constructor}
    assert [(item.class_name, item.assigned_name) for item in constructors["int"].local_instantiations] == [("Foo", "integer_local")]
    assert [(item.class_name, item.assigned_name) for item in constructors["float"].local_instantiations] == [
        ("Foo", "float_local"),
        ("Foo", "another_float_local"),
    ]
    for normalized_class in (owner, inline):
        assert assignment(normalized_class, "supplied_", "supplied").type_name == "Foo"
        assert assignment(normalized_class, "created_", "constructed").type_name == "Foo"
        assert assignment(normalized_class, "value_", "constructed").type_name == "Foo"
        assert assignment(normalized_class, "empty_", "constructed").type_name == "Foo"
