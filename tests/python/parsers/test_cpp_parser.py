import pytest

from python2uml.analyzers.class_analyzer import ClassAnalyzer
from python2uml.analyzers.relationship_analyzer import RelationshipAnalyzer
from python2uml.model.enums import ClassKind, ProjectLanguage, RelationshipType
from python2uml.parsers.abstracter import AbstractSyntaxTreeLoader
from python2uml.parsers.cpp_parser import CppParser


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


def test_cpp_parser_preserves_return_and_member_qualifiers_when_linking_overloads(tmp_path):
    header = write_source(
        tmp_path,
        "views.hpp",
        """
class Foo {};

class View {
public:
    Foo& get();
    const Foo& get() const;
    const Foo* pointer() const;
private:
    Foo value_;
};
""",
    )
    implementation = write_source(
        tmp_path,
        "views.cpp",
        """
Foo& View::get() {
    Foo mutable_local;
    return value_;
}

const Foo& View::get() const {
    Foo const_local;
    Foo second_const_local;
    return value_;
}

const Foo* View::pointer() const { return &value_; }
""",
    )

    view = class_by_name(CppParser().parse(str(header), str(implementation))[0], "View")
    methods = {method.return_type: method for method in view.methods if method.name in {"get", "pointer"}}

    assert set(methods) == {"Foo&", "const Foo&", "const Foo*"}
    assert [(item.class_name, item.assigned_name) for item in methods["Foo&"].local_instantiations] == [("Foo", "mutable_local")]
    assert [(item.class_name, item.assigned_name) for item in methods["const Foo&"].local_instantiations] == [
        ("Foo", "const_local"),
        ("Foo", "second_const_local"),
    ]


def test_cpp_empty_initializer_only_constructs_value_members(tmp_path):
    source = write_source(
        tmp_path,
        "empty.cpp",
        """
class Foo {};

class Owner {
public:
    Owner(Foo& reference) : pointer_(), reference_(reference), value_() {}
private:
    Foo* pointer_;
    Foo& reference_;
    Foo value_;
};
""",
    )

    owner = class_by_name(CppParser().parse(str(source))[0], "Owner")

    assert {(item.member_name, item.type_name) for item in owner.member_assignments if item.ownership == "constructed"} == {("value_", "Foo")}


def test_cpp_signature_spelling_and_relationship_endpoints_are_distinct(tmp_path):
    header = write_source(
        tmp_path,
        "signatures.hpp",
        """
class Foo {};

class PointerOnly {
public:
    void take(Foo* value);
};

class LeadingOnly {
public:
    const Foo& get();
};

class EastOnly {
public:
    Foo const& get();
};
""",
    )
    implementation = write_source(
        tmp_path,
        "signatures.cpp",
        """
void PointerOnly::take(Foo* value) {}
const Foo& LeadingOnly::get() { return *static_cast<Foo*>(nullptr); }
Foo const& EastOnly::get() { return *static_cast<Foo*>(nullptr); }
""",
    )

    modules = CppParser().parse(str(header), str(implementation))
    classes = {item.name: item for module in modules for item in module.classes}

    assert classes["PointerOnly"].methods[0].parameters[0].type_name == "Foo*"
    assert classes["LeadingOnly"].methods[0].return_type == "const Foo&"
    assert classes["EastOnly"].methods[0].return_type == "Foo const&"
    for name in ("PointerOnly", "LeadingOnly", "EastOnly"):
        assert "Foo" in {item.type_name for item in classes[name].type_references}
        assert classes[name].member_assignments == []
        assert all(not method.local_instantiations for method in classes[name].methods)

    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    relationships = {(item.source, item.target, item.relationship_type) for item in diagram.relationships}
    assert {(name, "Foo", RelationshipType.ASSOCIATION) for name in ("PointerOnly", "LeadingOnly", "EastOnly")} <= relationships


def test_cpp_top_level_parameter_cv_does_not_change_endpoint_or_overload_identity(tmp_path):
    header = write_source(
        tmp_path,
        "consumer.hpp",
        """
class Foo {};

class Consumer {
public:
    void take(Foo* const value);
    void watch(Foo* volatile value);
};
""",
    )
    implementation = write_source(
        tmp_path,
        "consumer.cpp",
        """
void Consumer::take(Foo* value) {
    Foo local;
}
""",
    )

    modules = CppParser().parse(str(header), str(implementation))
    consumer = class_by_name(modules[0], "Consumer")

    assert [method.name for method in consumer.methods].count("take") == 1
    take = next(method for method in consumer.methods if method.name == "take")
    assert [(item.class_name, item.assigned_name) for item in take.local_instantiations] == [("Foo", "local")]
    assert next(method for method in consumer.methods if method.name == "watch").parameters[0].type_name == "Foo* volatile"
    assert {item.type_name for item in consumer.type_references if item.context == "parameter"} == {"Foo"}

    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    assert ("Consumer", "Foo", RelationshipType.ASSOCIATION) in {(item.source, item.target, item.relationship_type) for item in diagram.relationships}


def test_cpp_parser_normalizes_member_push_back_of_parameter(tmp_path):
    source = write_source(
        tmp_path,
        "team.hpp",
        """
#include <vector>
class User {};
class Team {
public:
    void add(User* user) { members.push_back(user); }
private:
    std::vector<User*> members;
};
""",
    )

    team = class_by_name(CppParser().parse(str(source))[0], "Team")
    add = next(method for method in team.methods if method.name == "add")

    assert [(call.collection_attribute, call.item_name, call.item_type) for call in add.append_calls] == [("members", "user", "User")]


def test_cpp_parser_ignores_local_shadowed_and_static_push_back_targets(tmp_path):
    source = write_source(
        tmp_path,
        "local_team.hpp",
        """
#include <vector>
class User {};
class Team {
public:
    void add_local(User* user) {
        std::vector<User*> temporary;
        temporary.push_back(user);
    }
    void add_shadowed(User* user) {
        std::vector<User*> members;
        members.push_back(user);
    }
    void add_static(User* user) { shared.push_back(user); }
private:
    std::vector<User*> members;
    static std::vector<User*> shared;
};
""",
    )

    team = class_by_name(CppParser().parse(str(source))[0], "Team")

    assert all(not method.append_calls for method in team.methods)


def test_cpp_parser_ignores_collection_parameter_shadowing_field(tmp_path):
    source = write_source(
        tmp_path,
        "parameter_shadow.hpp",
        """
#include <vector>
class User {};
class Team {
public:
    void add(std::vector<User*>& members, User* user) { members.push_back(user); }
private:
    std::vector<User*> members;
};
""",
    )

    add = next(method for method in class_by_name(CppParser().parse(str(source))[0], "Team").methods if method.name == "add")

    assert add.append_calls == []


def test_cpp_parser_keeps_member_call_before_later_local_shadow(tmp_path):
    source = write_source(
        tmp_path,
        "later_shadow.hpp",
        """
#include <vector>
class User {};
class Team {
public:
    void add(User* user) {
        members.push_back(user);
        std::vector<User*> members;
    }
private:
    std::vector<User*> members;
};
""",
    )

    add = next(method for method in class_by_name(CppParser().parse(str(source))[0], "Team").methods if method.name == "add")

    assert [(call.collection_attribute, call.item_name, call.item_type) for call in add.append_calls] == [("members", "user", "User")]


def test_cpp_parser_does_not_leak_shadow_from_sibling_scope(tmp_path):
    source = write_source(
        tmp_path,
        "sibling_shadow.hpp",
        """
#include <vector>
class User {};
class Team {
public:
    void add(User* user, bool enabled) {
        if (enabled) {
            std::vector<User*> members;
            members.push_back(user);
        }
        members.push_back(user);
    }
private:
    std::vector<User*> members;
};
""",
    )

    add = next(method for method in class_by_name(CppParser().parse(str(source))[0], "Team").methods if method.name == "add")

    assert [(call.collection_attribute, call.item_name, call.item_type) for call in add.append_calls] == [("members", "user", "User")]


@pytest.mark.parametrize(
    "statement",
    [
        "for (std::vector<User*> members; !members.empty(); ) { members.push_back(user); }",
        "for (auto members : groups) { members.push_back(user); }",
        "if (std::vector<User*> members; enabled) { members.push_back(user); }",
    ],
    ids=["classic-for", "range-for", "if-initializer"],
)
def test_cpp_parser_respects_control_initializer_shadowing(tmp_path, statement):
    source = write_source(
        tmp_path,
        "control_shadow.hpp",
        f"""
#include <vector>
class User {{}};
class Team {{
public:
    void add(User* user, bool enabled) {{ {statement} }}
private:
    std::vector<User*> members;
}};
""",
    )

    add = next(method for method in class_by_name(CppParser().parse(str(source))[0], "Team").methods if method.name == "add")

    assert add.append_calls == []
