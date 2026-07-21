from parser.normalized_ast import NormalizedClass, NormalizedMemberAssignment, NormalizedModule, SourceDiagnostic


def test_normalized_module_carries_diagnostics_and_evidence():
    module = NormalizedModule(
        path="broken.java",
        classes=[NormalizedClass(name="Order", member_assignments=[NormalizedMemberAssignment("customer", "Customer", "supplied")])],
        diagnostics=[SourceDiagnostic("broken.java", 4, 9, "error", "unexpected token")],
    )
    assert module.classes[0].member_assignments[0].ownership == "supplied"
    assert module.diagnostics[0].line == 4
