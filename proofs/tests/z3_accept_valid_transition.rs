use z3::{ast::Int, ast::Ast, Config, Context, Solver};

#[test]
fn test_accept_valid_transition() {
    let cfg = Config::new();
    let ctx = Context::new(&cfg);
    let solver = Solver::new(&ctx);

    // Precondition: balance >= amount
    // Input: balance = 50, amount = 20

    let balance = Int::from_i64(&ctx, 50);
    let amount = Int::from_i64(&ctx, 20);

    let is_valid = balance.ge(&amount);
    solver.assert(&is_valid);

    // We expect SAT since 50 >= 20
    assert_eq!(solver.check(), z3::SatResult::Sat);
}
