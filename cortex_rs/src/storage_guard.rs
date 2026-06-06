use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;

const MAX_PROJECT_LENGTH: usize = 256;
const MAX_CONTENT_LENGTH: usize = 500_000;
const MIN_CONTENT_LENGTH: usize = 3;
const MAX_TAGS: usize = 50;
const MAX_TAG_LENGTH: usize = 128;

static POISON_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r"(?i);\s*DROP\s+TABLE").unwrap(),
        Regex::new(r"(?i);\s*DELETE\s+FROM").unwrap(),
        Regex::new(r"(?i)UNION\s+SELECT\s+").unwrap(),
        Regex::new(r"(?i)<\s*system\s*>").unwrap(),
        Regex::new(r"(?i)ignore\s+(?:all\s+)?previous\s+instructions").unwrap(),
        Regex::new(r"(?i)you\s+are\s+now\s+(?:a|an|DAN)").unwrap(),
        Regex::new(r"(?i)__cortex_override__").unwrap(),
    ]
});

#[pyfunction]
pub fn detect_poisoning(content: &str) -> bool {
    for pat in POISON_PATTERNS.iter() {
        if pat.is_match(content) {
            return true;
        }
    }
    false
}

#[pyfunction]
#[pyo3(signature = (project, content, fact_type, source, confidence, tags))]
pub fn validate_proposal(
    project: &str,
    content: &str,
    fact_type: &str,
    source: &str,
    confidence: &str,
    tags: Option<Vec<String>>,
) -> PyResult<Option<(String, String)>> {
    let project = project.trim();
    if project.is_empty() {
        return Ok(Some((
            "PROJECT_REQUIRED".to_string(),
            "project cannot be empty".to_string(),
        )));
    }
    if project.len() > MAX_PROJECT_LENGTH {
        return Ok(Some((
            "PROJECT_TOO_LONG".to_string(),
            format!("String should have at most {} characters", MAX_PROJECT_LENGTH),
        )));
    }

    let content = content.trim();
    if content.len() < MIN_CONTENT_LENGTH {
        return Ok(Some((
            "CONTENT_TOO_SHORT".to_string(),
            format!("content too short ({} chars, min {})", content.len(), MIN_CONTENT_LENGTH),
        )));
    }
    if content.len() > MAX_CONTENT_LENGTH {
        return Ok(Some((
            "CONTENT_TOO_LONG".to_string(),
            format!("String should have at most {} characters", MAX_CONTENT_LENGTH),
        )));
    }

    for pat in POISON_PATTERNS.iter() {
        if pat.is_match(content) {
            return Ok(Some((
                "POISONING_DETECTED".to_string(),
                "content rejected: suspicious pattern detected (possible data poisoning / prompt injection)".to_string(),
            )));
        }
    }

    let allowed_types = [
        "knowledge", "decision", "error", "ghost", "bridge", "preference", "identity", "issue",
        "world-model", "counterfactual", "rule", "axiom", "schema", "idea", "evolution", "test",
        "system_health", "discovery", "mafia_node", "telemetry_batch",
    ];
    if !allowed_types.contains(&fact_type) {
        return Ok(Some((
            "INVALID_FACT_TYPE".to_string(),
            format!("'{}' not in allowed types", fact_type),
        )));
    }

    let source = source.trim();
    if source.is_empty() {
        return Ok(Some((
            "SOURCE_REQUIRED".to_string(),
            "source attribution is mandatory. Use 'cli', 'agent:<name>', 'api', or 'human' as source.".to_string(),
        )));
    }

    let allowed_conf = [
        "C1", "C2", "C3", "C4", "C5", "stated", "inferred", "verified",
    ];
    if !allowed_conf.contains(&confidence) {
        return Ok(Some((
            "INVALID_CONFIDENCE".to_string(),
            format!("'{}' not in allowed confidence levels", confidence),
        )));
    }

    if let Some(t) = tags {
        if t.len() > MAX_TAGS {
            return Ok(Some((
                "TOO_MANY_TAGS".to_string(),
                format!("List should have at most {} items after validation", MAX_TAGS),
            )));
        }
        for tag in t {
            if tag.len() > MAX_TAG_LENGTH {
                return Ok(Some((
                    "INVALID_TAG".to_string(),
                    format!("invalid tag: {:?}", tag),
                )));
            }
        }
    }

    Ok(None)
}
