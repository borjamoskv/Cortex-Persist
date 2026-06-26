use z3::{ast::Int, ast::Ast, Config, Context, Solver};

#[test]
fn test_timeout_protection() {
    let mut cfg = Config::new();
    // Set a very strict timeout (e.g. 1ms) to protect against thermodynamic attacks
    cfg.set_param_value("timeout", "1");
    
    let ctx = Context::new(&cfg);
    let solver = Solver::new(&ctx);

    let x = Int::new_const(&ctx, "x");
    let y = Int::new_const(&ctx, "y");
    let z = Int::new_const(&ctx, "z");
    
    // Fermat's Last Theorem for n=3 (Z3 handles linear arithmetic well but non-linear over integers is undecidable/hard)
    let x3 = Int::mul(&ctx, &[&x, &x, &x]);
    let y3 = Int::mul(&ctx, &[&y, &y, &y]);
    let z3 = Int::mul(&ctx, &[&z, &z, &z]);
    
    let sum = Int::add(&ctx, &[&x3, &y3]);
    let equation = sum._eq(&z3);
    
    let x_gt_0 = x.gt(&Int::from_i64(&ctx, 0));
    let y_gt_0 = y.gt(&Int::from_i64(&ctx, 0));
    let z_gt_0 = z.gt(&Int::from_i64(&ctx, 0));

    solver.assert(&equation);
    solver.assert(&x_gt_0);
    solver.assert(&y_gt_0);
    solver.assert(&z_gt_0);

    // We expect the solver to timeout and return Unknown due to the 1ms limit
    assert_eq!(solver.check(), z3::SatResult::Unknown);
}
