// ============================================================
// PROBE MODULE — Async HTTP Endpoint Discovery
// Throughput: ~500 concurrent workers (network I/O bound)
// Fingerprinting: status, headers, tech stack detection
// ============================================================

use anyhow::Result;
use chrono::Utc;
use colored::*;
use dashmap::DashMap;
use futures::stream::{self, StreamExt};
use indicatif::{ProgressBar, ProgressStyle};
use reqwest::{Client, redirect::Policy};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, atomic::{AtomicU64, Ordering}};
use std::time::Duration;
use tokio::fs;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ProbeResult {
    pub url: String,
    pub status: u16,
    pub title: Option<String>,
    pub server: Option<String>,
    pub content_type: Option<String>,
    pub content_length: Option<u64>,
    pub technologies: Vec<String>,
    pub interesting_headers: Vec<String>,
    pub response_time_ms: u64,
    pub redirected_to: Option<String>,
    pub probed_at: String,
}

// Technology fingerprints (header + body patterns)
const TECH_FINGERPRINTS: &[(&str, &str)] = &[
    ("x-powered-by: php", "PHP"),
    ("x-powered-by: express", "Node.js/Express"),
    ("x-powered-by: asp.net", "ASP.NET"),
    ("server: nginx", "Nginx"),
    ("server: apache", "Apache"),
    ("server: iis", "IIS"),
    ("x-generator: wordpress", "WordPress"),
    ("x-drupal-cache", "Drupal"),
    ("x-joomla", "Joomla"),
    ("cf-ray", "Cloudflare"),
    ("x-amz-request-id", "AWS"),
    ("x-goog-", "Google Cloud"),
    ("x-azure-ref", "Azure"),
    ("x-shopify-stage", "Shopify"),
    ("x-vercel-id", "Vercel"),
    ("fly-request-id", "Fly.io"),
    ("x-wp-total", "WordPress REST API"),
];

// Security-relevant headers to capture
const INTERESTING_HEADERS: &[&str] = &[
    "access-control-allow-origin",
    "x-frame-options",
    "x-xss-protection",
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "x-api-version",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "authorization",
    "www-authenticate",
    "server-timing",
];

pub async fn run(
    input_file: String,
    concurrency: usize,
    timeout_secs: u64,
    output: String,
    follow_redirects: bool,
) -> Result<Vec<String>> {
    let content = match fs::read_to_string(&input_file).await {
        Ok(c) => c,
        Err(_) => {
            println!("{} No input file found: {}", "⚠".yellow(), input_file);
            return Ok(vec![]);
        }
    };

    let urls: Vec<String> = content
        .lines()
        .filter(|l| !l.is_empty() && (l.starts_with("http://") || l.starts_with("https://")))
        .map(|l| l.trim().to_string())
        .collect();

    if urls.is_empty() {
        println!("{} No valid URLs to probe", "⚠".yellow());
        return Ok(vec![]);
    }

    println!(
        "  {} {} endpoints | concurrency={} timeout={}s",
        "PROBE".bright_blue().bold(),
        urls.len().to_string().bright_white(),
        concurrency.to_string().yellow(),
        timeout_secs.to_string().yellow()
    );

    // Build HTTP client
    let redirect_policy = if follow_redirects {
        Policy::limited(5)
    } else {
        Policy::none()
    };

    let client = Arc::new(
        Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .redirect(redirect_policy)
            .danger_accept_invalid_certs(true) // bug bounty: expired/self-signed certs are common
            .use_rustls_tls()
            .user_agent("Mozilla/5.0 (compatible; BountyHunter/0.1; security-research)")
            .build()?
    );

    let pb = Arc::new(ProgressBar::new(urls.len() as u64));
    pb.set_style(
        ProgressStyle::with_template(
            "  [{elapsed_precise}] {bar:40.cyan/black} {pos}/{len} | {per_sec} | {msg}"
        )
        .unwrap()
        .progress_chars("█▓░"),
    );

    let results: Arc<DashMap<String, ProbeResult>> = Arc::new(DashMap::new());
    let live_count = Arc::new(AtomicU64::new(0));

    stream::iter(urls)
        .map(|url| {
            let client = Arc::clone(&client);
            let results = Arc::clone(&results);
            let pb = Arc::clone(&pb);
            let live = Arc::clone(&live_count);

            async move {
                pb.inc(1);
                let start = std::time::Instant::now();

                match client.get(&url).send().await {
                    Ok(resp) => {
                        let status = resp.status().as_u16();
                        let response_time_ms = start.elapsed().as_millis() as u64;

                        // Collect headers before consuming body
                        let server = resp
                            .headers()
                            .get("server")
                            .and_then(|v| v.to_str().ok())
                            .map(|s| s.to_string());

                        let content_type = resp
                            .headers()
                            .get("content-type")
                            .and_then(|v| v.to_str().ok())
                            .map(|s| s.to_string());

                        let content_length = resp.content_length();

                        let redirected_to = if resp.url().as_str() != url {
                            Some(resp.url().to_string())
                        } else {
                            None
                        };

                        // Fingerprint technologies from headers
                        let mut technologies = vec![];
                        let headers_str = format!("{:?}", resp.headers()).to_lowercase();

                        for (pattern, tech) in TECH_FINGERPRINTS {
                            if headers_str.contains(pattern) {
                                technologies.push(tech.to_string());
                            }
                        }

                        // Capture interesting security headers
                        let interesting: Vec<String> = INTERESTING_HEADERS
                            .iter()
                            .filter(|h| headers_str.contains(*h))
                            .map(|h| h.to_string())
                            .collect();

                        // Extract title from body (limited read)
                        let body = resp.text().await.unwrap_or_default();
                        let title = extract_title(&body);

                        // Body-based tech detection
                        let body_lower = body.to_lowercase();
                        if body_lower.contains("wp-content") { technologies.push("WordPress".to_string()); }
                        if body_lower.contains("joomla") { technologies.push("Joomla".to_string()); }
                        if body_lower.contains("drupal") { technologies.push("Drupal".to_string()); }
                        if body_lower.contains("react") { technologies.push("React".to_string()); }
                        if body_lower.contains("angular") { technologies.push("Angular".to_string()); }
                        if body_lower.contains("vue.js") || body_lower.contains("vuejs") {
                            technologies.push("Vue.js".to_string());
                        }
                        technologies.dedup();

                        // Only capture 2xx, 3xx, 401, 403, 405 (interesting status codes)
                        let is_interesting = matches!(status,
                            200..=299 | 301 | 302 | 307 | 308 | 401 | 403 | 405 | 500..=503
                        );

                        if is_interesting {
                            live.fetch_add(1, Ordering::Relaxed);

                            let status_colored = match status {
                                200..=299 => status.to_string().green().to_string(),
                                300..=399 => status.to_string().yellow().to_string(),
                                401 | 403 => status.to_string().red().to_string(),
                                _ => status.to_string().dimmed().to_string(),
                            };
                            pb.set_message(format!("[{}] {}", status_colored, url.bright_white()));

                            let probe = ProbeResult {
                                url: url.clone(),
                                status,
                                title,
                                server,
                                content_type,
                                content_length,
                                technologies,
                                interesting_headers: interesting,
                                response_time_ms,
                                redirected_to,
                                probed_at: Utc::now().to_rfc3339(),
                            };
                            results.insert(url, probe);
                        }
                    }
                    Err(_) => {} // Connection refused, timeout — skip
                }
            }
        })
        .buffer_unordered(concurrency)
        .collect::<Vec<_>>()
        .await;

    let live = live_count.load(Ordering::Relaxed);
    pb.finish_with_message(format!("{} live endpoints", live.to_string().bright_green()));

    let mut found: Vec<ProbeResult> = results
        .iter()
        .map(|e| e.value().clone())
        .collect();
    found.sort_by(|a, b| a.url.cmp(&b.url));

    // Save output
    if let Some(parent) = std::path::Path::new(&output).parent() {
        let _ = fs::create_dir_all(parent).await;
    }
    let json = serde_json::to_string_pretty(&found)?;
    fs::write(&output, json).await?;

    // Summary table
    print_probe_summary(&found);

    let live_urls: Vec<String> = found
        .iter()
        .filter(|r| (200..=299).contains(&r.status))
        .map(|r| r.url.clone())
        .collect();

    Ok(live_urls)
}

fn extract_title(html: &str) -> Option<String> {
    let lower = html.to_lowercase();
    let start = lower.find("<title")?;
    let start = html[start..].find('>')? + start + 1;
    let end = html[start..].to_lowercase().find("</title>")? + start;
    let title = html[start..end].trim().to_string();
    if title.is_empty() { None } else { Some(title) }
}

fn print_probe_summary(results: &[ProbeResult]) {
    if results.is_empty() { return; }

    println!("\n  {}", "── PROBE RESULTS ──".bright_blue().bold());
    println!(
        "  {:<50} {:<6} {:<10} {:<20}",
        "URL".dimmed(),
        "STATUS".dimmed(),
        "TIME(ms)".dimmed(),
        "TECH".dimmed()
    );
    println!("  {}", "─".repeat(90).dimmed());

    for r in results.iter().take(50) {
        let status_str = match r.status {
            200..=299 => r.status.to_string().green().to_string(),
            300..=399 => r.status.to_string().yellow().to_string(),
            401 | 403 => r.status.to_string().bright_red().to_string(),
            _ => r.status.to_string().dimmed().to_string(),
        };
        let url_display = if r.url.len() > 48 {
            format!("{}…", &r.url[..47])
        } else {
            r.url.clone()
        };
        println!(
            "  {:<50} {:<6} {:<10} {}",
            url_display,
            status_str,
            r.response_time_ms,
            r.technologies.join(", ").dimmed()
        );
    }

    if results.len() > 50 {
        println!("  {} … {} more results in output file", "".dimmed(), results.len() - 50);
    }
}
