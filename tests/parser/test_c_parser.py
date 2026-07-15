from pathlib import Path

from analyzers.class_analyzer import ClassAnalyzer
from analyzers.relationship_analyzer import RelationshipAnalyzer
from model.enums import ClassKind, RelationshipType
from parser.c_parser import CParser


def write_source(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def class_by_name(modules, name):
    return next(item for module in modules for item in module.classes if item.name == name)


def file_class(module):
    return next(item for item in module.classes if item.parent is None)


def assignment(normalized_class, member):
    return next(item for item in normalized_class.member_assignments if item.member_name == member)


def test_c_parser_models_files_structs_macros_globals_and_function_ownership(tmp_path):
    header = write_source(
        tmp_path,
        "shop.h",
        """
#define MAX_ITEMS 20
#define CLAMP(value, limit) ((value) < (limit) ? (value) : (limit))

typedef struct Owner {
    int id;
} Owner;

typedef struct Cart {
    Owner owner;
    Owner *backup_owner;
} Cart;

struct Receipt {
    Cart cart;
};

struct Coupon { int code; };

struct Warehouse {
    struct Bin { int id; } bin;
};

extern int shop_open;
void cart_add(Cart *self, Owner owner);
void cart_apply(Cart *self, Coupon *coupon);
void shop_reset(void);
Cart *shop_cart(void);
""",
    )
    implementation = write_source(
        tmp_path,
        "shop.c",
        """
#include "shop.h"
int shop_open = 1;

void cart_add(Cart *self, Owner owner) {
    Owner local_owner;
}

void cart_apply(Cart *self, Coupon *coupon) {}

void shop_reset(void) {}
Cart *shop_cart(void) { return 0; }
""",
    )

    modules = CParser().parse(str(header), str(implementation))
    header_class, implementation_class = map(file_class, modules)
    owner = class_by_name(modules, "Owner")
    cart = class_by_name(modules, "Cart")
    receipt = class_by_name(modules, "Receipt")
    warehouse = class_by_name(modules, "Warehouse")
    bin_class = class_by_name(modules, "Bin")

    assert header_class.name != implementation_class.name
    assert owner.parent == header_class.name
    assert cart.parent == header_class.name
    assert receipt.parent == header_class.name
    assert bin_class.parent == header_class.name
    assert cart.kind is ClassKind.STRUCT
    assert {item.name for item in header_class.attributes} >= {"MAX_ITEMS", "CLAMP", "shop_open"}
    assert {item.name for item in implementation_class.attributes} == {"shop_open"}
    assert [item.name for item in cart.methods] == ["cart_add", "cart_apply"]
    assert [item.name for item in implementation_class.methods] == ["shop_reset", "shop_cart"]
    assert implementation_class.methods[1].return_type == "Cart*"
    assert [item.name for item in cart.methods[0].parameters] == ["owner"]
    assert [(item.class_name, item.assigned_name) for item in cart.methods[0].local_instantiations] == [("Owner", "local_owner")]
    assert assignment(cart, "owner").ownership == "value"
    assert assignment(cart, "backup_owner").ownership == "reference"
    assert assignment(receipt, "cart").ownership == "value"
    assert assignment(warehouse, "bin").type_name == "Bin"
    assert (header_class.name, "include") in {(item.type_name, item.context) for item in implementation_class.type_references}

    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    relationships = {(item.source, item.target, item.relationship_type) for item in diagram.relationships}
    assert (cart.name, owner.name, RelationshipType.COMPOSITION) in relationships
    assert (receipt.name, cart.name, RelationshipType.COMPOSITION) in relationships
    assert (cart.name, "Coupon", RelationshipType.ASSOCIATION) in relationships
    assert (implementation_class.name, cart.name, RelationshipType.ASSOCIATION) in relationships
    assert (implementation_class.name, header_class.name, RelationshipType.ASSOCIATION) in relationships


def test_c_parser_handles_anonymous_typedef_struct_and_recoverable_syntax_error(tmp_path):
    source = write_source(
        tmp_path,
        "model.h",
        """
typedef struct {
    int id;
} AnonymousRecord;

struct Broken {
    int valid;
};
@
""",
    )

    module = CParser().parse(str(source))[0]

    assert class_by_name([module], "AnonymousRecord").parent == file_class(module).name
    assert "valid" in {item.name for item in class_by_name([module], "Broken").attributes}
    assert module.diagnostics
    assert module.diagnostics[0].path == str(source)


def test_c_file_class_names_are_stable_and_collision_safe(tmp_path):
    first = write_source(tmp_path, "one/model.h", "struct First { int id; };\n")
    second = write_source(tmp_path, "two/model.h", "struct Second { int id; };\n")
    parser = CParser()

    forward = parser.parse(str(first), str(second))
    reverse = parser.parse(str(second), str(first))
    forward_names = {Path(module.path): file_class(module).name for module in forward}
    reverse_names = {Path(module.path): file_class(module).name for module in reverse}

    assert len(set(forward_names.values())) == 2
    assert forward_names == reverse_names
