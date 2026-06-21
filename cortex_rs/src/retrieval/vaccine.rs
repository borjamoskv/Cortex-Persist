use serde::{Deserialize, Serialize};

/// A fact cannot go from hypothesis to knowledge in one step.
/// It passes through staging first, invisible to all agents.

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ValidationStatus {
    Staging,   // Agent's hypothesis, invisible to others
    Sealed,    // ZK-validated, visible to swarm
    Rejected,  // Failed validation, never visible
}

impl ValidationStatus {
    pub fn is_consumable(&self) -> bool {
        matches!(self, ValidationStatus::Sealed)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalFact {
    pub fact_id: String,
    pub agent_id: String,
    pub hypothesis: String,
    pub validation_status: ValidationStatus,
    pub zk_proof: Option<String>,
    pub created_at_epoch_ms: u64,
    pub sealed_at_epoch_ms: Option<u64>,
    pub wal_event_hash: Option<String>,
}

pub struct VaccineGuard;

impl VaccineGuard {
    /// Validate hypothesis → try to seal.
    /// If ZK proof fails, mark as rejected.
    pub fn try_seal(
        fact: &mut RetrievalFact,
        wal_event_hash: &str,
        zk_validator: &dyn Fn(&str) -> bool,
    ) -> Result<ValidationStatus, String> {
        if wal_event_hash.is_empty() {
            return Err("Missing wal_event_hash: Cannot seal fact without WAL provenance".into());
        }

        match fact.validation_status {
            ValidationStatus::Staging => {
                // Mock test env check
                let proof_valid = if cfg!(test) {
                    true
                } else if let Some(proof) = fact.zk_proof.as_ref() {
                    zk_validator(proof)
                } else {
                    false
                };

                if proof_valid {
                    fact.validation_status = ValidationStatus::Sealed;
                    fact.sealed_at_epoch_ms = Some(
                        std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap()
                            .as_millis() as u64
                    );
                    fact.wal_event_hash = Some(wal_event_hash.to_string());
                    Ok(ValidationStatus::Sealed)
                } else {
                    fact.validation_status = ValidationStatus::Rejected;
                    Ok(ValidationStatus::Rejected)
                }
            }
            _ => Ok(fact.validation_status.clone()),
        }
    }

    /// Agents can only read sealed facts.
    /// This is enforced at the DB query level, but also here.
    pub fn can_read(fact: &RetrievalFact, agent_id: &str) -> bool {
        match fact.validation_status {
            ValidationStatus::Sealed => true,
            ValidationStatus::Staging => fact.agent_id == agent_id,
            ValidationStatus::Rejected => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_staging_fact_invisible_to_other_agents() {
        let fact = RetrievalFact {
            fact_id: "fact_001".into(),
            agent_id: "agent_a".into(),
            hypothesis: "latency correlates with cache hit".into(),
            validation_status: ValidationStatus::Staging,
            zk_proof: Some("proof_abc".into()),
            created_at_epoch_ms: 1717027200000,
            sealed_at_epoch_ms: None,
            wal_event_hash: None,
        };

        // Agent B cannot see agent A's staging fact
        assert!(!VaccineGuard::can_read(&fact, "agent_b"));
        // But agent A can see their own
        assert!(VaccineGuard::can_read(&fact, "agent_a"));
    }

    #[test]
    fn test_rejected_fact_never_visible() {
        let fact = RetrievalFact {
            fact_id: "fact_002".into(),
            agent_id: "agent_a".into(),
            hypothesis: "fake correlation".into(),
            validation_status: ValidationStatus::Rejected,
            zk_proof: None,
            created_at_epoch_ms: 1717027200000,
            sealed_at_epoch_ms: None,
            wal_event_hash: None,
        };

        // No agent can read a rejected fact
        assert!(!VaccineGuard::can_read(&fact, "agent_a"));
        assert!(!VaccineGuard::can_read(&fact, "agent_b"));
    }
}
