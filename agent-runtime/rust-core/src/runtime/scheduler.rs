use super::action::Action;

pub struct Scheduler;

impl Scheduler {
    pub fn schedule(mut actions: Vec<Action>) -> Vec<Action> {
        // DeepMind-style control spine: Truncate lower-expected-value branches
        actions.sort_by(|a, b| b.expected_value.partial_cmp(&a.expected_value).unwrap_or(std::cmp::Ordering::Equal));
        actions.truncate(5);
        actions
    }
}
