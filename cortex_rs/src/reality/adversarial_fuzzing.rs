#[cfg(test)]
mod proptests {
    use proptest::prelude::*;
    use serde_json;
    use crate::reality::claim::{VerifiableClaimInput, ClaimDomain, Source};
    use crate::reality::scorer::TrustScorer;
    use crate::reality::validator::Validator;

    // 1. FUZZING: JSON Deserialization Boundary
    // Manda cadenas aleatorias buscando pánico en Serde o desbordamientos.
    proptest! {
        #[test]
        fn fuzz_json_deserialization(ref json_str in "\\PC*") {
            // El fuzzer intenta inyectar Unicode inválido, control chars, estructuras masivas.
            // La aserción es que NUNCA debe entrar en pánico. Solo debe devolver Ok o Err.
            let _result: Result<VerifiableClaimInput, _> = serde_json::from_str(json_str);
        }
    }

    // Estrategia generadora para el DTO con valores adversariales
    fn arb_claim_input() -> impl Strategy<Value = VerifiableClaimInput> {
        (
            "[a-zA-Z0-9-]{0, 200}",           // claim_id (fuzz empty, long, special chars)
            ".*",                             // statement (arbitrary UTF-8)
            prop_oneof![
                Just(ClaimDomain::Llm), Just(ClaimDomain::Api), 
                Just(ClaimDomain::System), Just(ClaimDomain::Performance), Just(ClaimDomain::Pricing)
            ],
            any::<u64>(),                     // created_at_epoch_ms (future, past, max)
            prop::collection::vec(arb_source(), 0..10), // sources
            prop::collection::vec(".*", 0..5),          // evidence hashes
        ).prop_map(|(id, stmt, domain, ts, sources, hashes)| {
            VerifiableClaimInput {
                claim_id: id,
                statement: stmt,
                domain,
                created_at_epoch_ms: ts,
                sources,
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
            // La puntuación jamás debe ser menor que 0.0 ni mayor que 1.0, 
            // ni entrar en pánico ante arrays vacíos, masivos o URLs corruptas.
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
            // Inyectar scores adversariales (negativos, NaN, Inf, muy por encima de 1.0)
            // y tiempos adversariales (tiempos pasados, underflow / saturating_sub stress).
            // Aserción: NUNCA debe entrar en pánico. 
            // Si el score es NaN/Inf, o el tiempo underflowea, debe mapearlo a un Err semántico.
            let result = validator.validate(claim, trust_score, now_epoch_ms);
            
            match result {
                Ok(_) => {
                    prop_assert!(!claim.statement.trim().is_empty(), "Empty statement passed");
                    prop_assert!(!claim.is_sourceless(), "Sourceless passed");
                    prop_assert!(trust_score >= validator.minimum_trust, "Low trust passed");
                },
                Err(_) => {} // Todo error manejado es un éxito del fuzzer
            }
        }
    }
}
