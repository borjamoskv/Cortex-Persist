use crate::reality::claim::VerifiableClaimInput;

#[derive(Debug)]
pub enum ValidationError {
    NoSources,
    TrustTooLow { actual: f32, minimum: f32 },
    StatementEmpty,
    StaleSource { url: String, age_days: u64 },
    StorageFailure { reason: String },
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoSources =>
                write!(f, "Claim rejected: no sources provided"),
            Self::TrustTooLow { actual, minimum } =>
                write!(f, "Trust score {actual:.2} below minimum {minimum:.2}"),
            Self::StatementEmpty =>
                write!(f, "Claim rejected: empty statement"),
            Self::StaleSource { url, age_days } =>
                write!(f, "Source stale ({age_days} days): {url}"),
            Self::StorageFailure { reason } =>
                write!(f, "Storage failure: {reason}"),
        }
    }
}

pub struct Validator {
    pub minimum_trust: f32,
    pub max_source_age_days: u64,
}

impl Default for Validator {
    fn default() -> Self {
        Self {
            minimum_trust: 0.60,
            max_source_age_days: 90,
        }
    }
}

impl Validator {
    pub fn validate(
        &self,
        claim: &VerifiableClaimInput,
        trust_score: f32,
        now_epoch_ms: u64,
    ) -> Result<(), ValidationError> {
        if claim.statement.trim().is_empty() {
            return Err(ValidationError::StatementEmpty);
        }

        if claim.is_sourceless() {
            return Err(ValidationError::NoSources);
        }

        if trust_score < self.minimum_trust {
            return Err(ValidationError::TrustTooLow {
                actual: trust_score,
                minimum: self.minimum_trust,
            });
        }

        let max_age_ms = self.max_source_age_days * 86_400_000;
        for source in &claim.sources {
            let age_ms = now_epoch_ms.saturating_sub(source.fetched_at_epoch_ms);
            if age_ms > max_age_ms {
                let age_days = age_ms / 86_400_000;
                return Err(ValidationError::StaleSource {
                    url: source.url.clone(),
                    age_days,
                });
            }
        }

        Ok(())
    }
}
