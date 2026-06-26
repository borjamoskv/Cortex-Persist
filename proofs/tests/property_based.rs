use proptest::prelude::*;
use z3::{ast::Int, ast::Ast, Config, Context, Solver};

proptest! {
    #[test]
    fn test_property_based_balance_validation(balance_val in -1000..1000i64, amount_val in 0..1000i64) {
        let cfg = Config::new();
        let ctx = Context::new(&cfg);
        let solver = Solver::new(&ctx);

        let balance = Int::from_i64(&ctx, balance_val);
        let amount = Int::from_i64(&ctx, amount_val);

        let is_valid = balance.ge(&amount);
        solver.assert(&is_valid);

        let expected = if balance_val >= amount_val {
            z3::SatResult::Sat
        } else {
            z3::SatResult::Unsat
        };

        prop_assert_eq!(solver.check(), expected);
    }
}
