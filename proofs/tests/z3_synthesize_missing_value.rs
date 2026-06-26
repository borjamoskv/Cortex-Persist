use z3::{ast::Int, ast::Ast, Config, Context, Solver};

#[test]
fn test_synthesize_missing_value() {
    let cfg = Config::new();
    let ctx = Context::new(&cfg);
    let solver = Solver::new(&ctx);

    // Given formula: x + y = 10
    // Input: x = 4, y is missing (must be synthesized)

    let x = Int::from_i64(&ctx, 4);
    let y = Int::new_const(&ctx, "y");
    let ten = Int::from_i64(&ctx, 10);

    let sum = Int::add(&ctx, &[&x, &y]);
    let equation = sum._eq(&ten);
    
    solver.assert(&equation);

    assert_eq!(solver.check(), z3::SatResult::Sat);
    
    let model = solver.get_model().unwrap();
    let y_val = model.eval(&y, true).unwrap().as_i64().unwrap();
    
    // Z3 does not "guess text", it synthesizes formal propositional logic constraints.
    assert_eq!(y_val, 6);
}
