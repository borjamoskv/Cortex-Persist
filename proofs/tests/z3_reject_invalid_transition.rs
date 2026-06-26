use z3::{ast::Int, ast::Ast, Config, Context, Solver};

#[test]
fn test_reject_invalid_transition() {
    let cfg = Config::new();
    let ctx = Context::new(&cfg);
    let solver = Solver::new(&ctx);

    // Precondition: balance >= amount
    // Input: balance = 10, amount = 20

    let balance = Int::from_i64(&ctx, 10);
    let amount = Int::from_i64(&ctx, 20);

    // Assert the state constraint: balance must be >= amount to allow transition
    let is_valid = balance.ge(&amount);
    solver.assert(&is_valid);

    // We expect the solver to find NO valid model satisfying this, hence UNSAT.
    assert_eq!(solver.check(), z3::SatResult::Unsat);
}
