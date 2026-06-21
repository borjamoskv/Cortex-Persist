use crate::reality::claim::Source;

pub enum SourceClass {
    Official,
    TechnicalDocs,
    Community,
    Unknown,
}

pub struct TrustScorer;

impl TrustScorer {
    pub fn score(sources: &[Source], multi_source: bool) -> f32 {
        if sources.is_empty() {
            return 0.0;
        }

        let base = Self::base_score(sources);

        // Bonus por múltiples fuentes independientes
        let multi_bonus = if multi_source && sources.len() >= 2 {
            0.10
        } else {
            0.0
        };

        (base + multi_bonus).min(1.0)
    }

    fn base_score(sources: &[Source]) -> f32 {
        sources
            .iter()
            .map(|s| Self::score_url(&s.url))
            .fold(0.0_f32, f32::max)
    }

    fn classify_url(url: &str) -> SourceClass {
        let official = [
            "ai.google.dev",
            "platform.openai.com",
            "docs.anthropic.com",
            "cloud.google.com",
            "github.com/google",
            "github.com/openai",
        ];

        let technical_docs = [
            "docs.",
            "developers.",
            "api.",
        ];

        let weak_sources = [
            "reddit.com",
            "twitter.com",
            "x.com",
            "medium.com",
        ];

        if official.iter().any(|d| url.contains(d)) {
            return SourceClass::Official;
        }

        if technical_docs.iter().any(|d| url.contains(d)) {
            return SourceClass::TechnicalDocs;
        }

        if weak_sources.iter().any(|d| url.contains(d)) {
            return SourceClass::Community;
        }

        SourceClass::Unknown
    }

    fn score_url(url: &str) -> f32 {
        let class = Self::classify_url(url);
        // Map to heuristic lower-bound ranges to prevent fake precision
        match class {
            SourceClass::Official => 0.90,       // Deterministic lower bound for official
            SourceClass::TechnicalDocs => 0.75,  // Documentation
            SourceClass::Community => 0.30,      // Weak signals
            SourceClass::Unknown => 0.40,        // Unknown baseline
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_sources_always_zero() {
        assert_eq!(TrustScorer::score(&[], false), 0.0);
    }

    #[test]
    fn test_official_source_scores_high() {
        let sources = vec![Source {
            url: "https://ai.google.dev/gemini-api/docs".to_string(),
            fetch_hash: "abc123".to_string(),
            fetched_at_epoch_ms: 1717027200000,
        }];
        let score = TrustScorer::score(&sources, false);
        assert!(score >= 0.85, "official source must score >= 0.85, got {score}");
    }

    #[test]
    fn test_llm_generated_claim_is_zero() {
        let score = TrustScorer::score(&[], false);
        assert_eq!(score, 0.0);
    }
}
