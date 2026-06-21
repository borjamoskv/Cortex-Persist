#[cfg(test)]
mod proptests {
    use proptest::prelude::*;
    use serde_json;
    use crate::reality::claim::{RealityClaim, ClaimDomain, Source, ClaimStatus};
    use crate::reality::scorer::TrustScorer;
    use crate::reality::validator::Validator;

    // 1. FUZZING: JSON Deserialization Boundary
    proptest! {
        #[test]
        fn fuzz_json_deserialization(ref json_str in "\\PC*") {
            let _result: Result<RealityClaim, _> = serde_json::from_str(json_str);
        }
    }

    // Estrategia generadora para el DTO con valores adversariales
    fn arb_claim_input() -> impl Strategy<Value = RealityClaim> {
        (
            "[a-zA-Z0-9-]{0, 200}",           // claim_id (fuzz empty, long, special chars)
            ".*",                             // statement (arbitrary UTF-8)
            prop_oneof![
                Just(ClaimDomain::Llm), Just(ClaimDomain::Api), 
                Just(ClaimDomain::System), Just(ClaimDomain::Performance), Just(ClaimDomain::Pricing)
            ],
            any::<u64>(),                     // created_at_epoch_ms (future, past, max)
            prop::collection::vec(arb_source(), 0..10), // sources
            any::<f32>(),                     // trust_score
            prop_oneof![
                Just(ClaimStatus::Pending), Just(ClaimStatus::Verified),
                Just(ClaimStatus::Rejected), Just(ClaimStatus::Unknown)
            ],
            prop::collection::vec(".*", 0..5),          // evidence hashes
        ).prop_map(|(id, stmt, domain, ts, sources, trust_score, status, hashes)| {
            RealityClaim {
                claim_id: id,
                statement: stmt,
                domain,
                created_at_epoch_ms: ts,
                sources,
                trust_score,
                status,
                evidence_hashes: hashes,
            }
        })
    }

    fn arb_source() -> impl Strategy<Value = Source> {
        (
            ".*",            // url (fuzzing domain names and massive URLs)
            ".*",            // fetch_hash
            any::<u64>(),    // fetched_at_epoch_ms (can be massive, future, zero)
        ).prop_map(|(url, fetch_hash, fetched_at_epoch_ms)| {
            Source { url, fetch_hash, fetched_at_epoch_ms }
        })
    }

    // 2. FUZZING: Trust Scorer
    proptest! {
        #[test]
        fn fuzz_trust_scorer(ref claim in arb_claim_input()) {
            let multi = claim.sources.len() >= 2;
            let score = TrustScorer::score(&claim.sources, multi);
            prop_assert!(score >= 0.0 && score <= 1.0, "Score {} is out of bounds [0.0, 1.0]", score);
            prop_assert!(!score.is_nan(), "Score cannot be NaN");
            prop_assert!(!score.is_infinite(), "Score cannot be Infinite");
        }
    }

    // 3. FUZZING: Validator
    proptest! {
        #[test]
        fn fuzz_validator(ref claim in arb_claim_input(), trust_score in -100.0f32..100.0f32, now_epoch_ms in any::<u64>()) {
            let validator = Validator::default();
            let mut claim_mut = claim.clone();
            claim_mut.trust_score = trust_score;
            let result = validator.validate(&claim_mut, now_epoch_ms);
            
            match result {
                Ok(_) => {
                    prop_assert!(!claim_mut.statement.trim().is_empty(), "Empty statement passed");
                    prop_assert!(!claim_mut.is_sourceless(), "Sourceless passed");
                    prop_assert!(claim_mut.trust_score >= validator.minimum_trust, "Low trust passed");
                },
                Err(_) => {} // Todo error manejado es un éxito del fuzzer
            }
        }
    }
}
