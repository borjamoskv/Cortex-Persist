use regex::Regex;
use std::sync::OnceLock;

static SECRET_KEY_REGEX: OnceLock<Regex> = OnceLock::new();
static CRYPTO_MAT_REGEX: OnceLock<Regex> = OnceLock::new();
static ENDPOINT_REGEX: OnceLock<Regex> = OnceLock::new();
static HIGH_ENTROPY_REGEX: OnceLock<Regex> = OnceLock::new();

pub struct SecretHeuristics;

impl SecretHeuristics {
    fn get_key_regex() -> &'static Regex {
        SECRET_KEY_REGEX.get_or_init(|| {
            Regex::new(r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key)\s*[:=]\s*\S+").unwrap()
        })
    }

    fn get_crypto_regex() -> &'static Regex {
        CRYPTO_MAT_REGEX.get_or_init(|| {
            Regex::new(r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----").unwrap()
        })
    }

    fn get_endpoint_regex() -> &'static Regex {
        ENDPOINT_REGEX.get_or_init(|| {
            Regex::new(r"https?:\/\/[^\s]+\/(admin|internal|debug|graphql)").unwrap()
        })
    }

    fn get_high_entropy_regex() -> &'static Regex {
        HIGH_ENTROPY_REGEX.get_or_init(|| {
            Regex::new(r"\b[A-Za-z0-9+/]{40,}={0,2}\b").unwrap()
        })
    }

    /// Evaluates Shannon Entropy for a given string slice.
    pub fn shannon_entropy(s: &str) -> f64 {
        let mut map = [0_usize; 256];
        let mut len = 0;
        for &b in s.as_bytes() {
            map[b as usize] += 1;
            len += 1;
        }
        if len == 0 {
            return 0.0;
        }
        let mut entropy = 0.0;
        for &count in &map {
            if count > 0 {
                let p = count as f64 / len as f64;
                entropy -= p * p.log2();
            }
        }
        entropy
    }

    /// Evaluates if a given payload matches any secret heuristic or has high entropy.
    pub fn is_secret(payload: &str) -> bool {
        Self::get_key_regex().is_match(payload) ||
        Self::get_crypto_regex().is_match(payload) ||
        Self::get_endpoint_regex().is_match(payload) ||
        (Self::get_high_entropy_regex().is_match(payload) && Self::shannon_entropy(payload) > 4.2)
    }

    /// Redacts identified secrets from the payload.
    pub fn redact(payload: &str) -> String {
        let mut redacted = payload.to_string();
        redacted = Self::get_key_regex().replace_all(&redacted, "[REDACTED: CORTEX-PURGE-KEY]").to_string();
        redacted = Self::get_crypto_regex().replace_all(&redacted, "[REDACTED: CORTEX-PURGE-CRYPTO]").to_string();
        redacted = Self::get_endpoint_regex().replace_all(&redacted, "[REDACTED: CORTEX-PURGE-ENDPOINT]").to_string();
        
        // Custom replacement for high entropy
        let high_entropy_re = Self::get_high_entropy_regex();
        redacted = high_entropy_re.replace_all(&redacted, |caps: &regex::Captures| {
            let matched_str = &caps[0];
            if Self::shannon_entropy(matched_str) > 4.2 {
                "[REDACTED: CORTEX-PURGE-ENTROPY]".to_string()
            } else {
                matched_str.to_string()
            }
        }).to_string();

        redacted
    }
}
