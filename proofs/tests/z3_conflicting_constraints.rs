use z3::{ast::Int, ast::Ast, Config, Context, Solver};

#[test]
fn test_conflicting_constraints() {
    let cfg = Config::new();
    let ctx = Context::new(&cfg);
    let solver = Solver::new(&ctx);

    // Simulated LLM hallucination where it emits two conflicting facts:
    // Fact 1: Node status = 1 (Active)
    // Fact 2: Node status = 0 (Inactive)

    let status = Int::new_const(&ctx, "status");
    let active = Int::from_i64(&ctx, 1);
    let inactive = Int::from_i64(&ctx, 0);

    let is_active = status._eq(&active);
    let is_inactive = status._eq(&inactive);

    // The LLM hallucinated both constraints simultaneously
    solver.assert(&is_active);
    solver.assert(&is_inactive);

    // Z3 correctly identifies the contradiction (UNSAT)
    assert_eq!(solver.check(), z3::SatResult::Unsat);
}
