use super::action::Action;
use super::state::State;

pub struct SafetyFilter;

impl SafetyFilter {
    pub fn apply(actions: Vec<Action>, state: &State) -> Option<Action> {
        actions
            .into_iter()
            .filter(|a| Self::hard_constraints(a, state))
            // Retrieve action with maximum expected value from the allowed ones
            .max_by(|a, b| a.expected_value.partial_cmp(&b.expected_value).unwrap_or(std::cmp::Ordering::Equal))
    }

    fn hard_constraints(action: &Action, state: &State) -> bool {
        // C5-REAL Anti-entropy logic: Discard if operation matches blacklist
        !state.blacklist.iter().any(|b| action.op.contains(b))
    }
}
