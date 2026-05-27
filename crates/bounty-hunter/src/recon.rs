// ============================================================
// RECON MODULE — Subdomain Enumeration + DNS Resolution
// Throughput: ~2000 concurrent DNS resolvers (I/O bound)
// ============================================================

use anyhow::Result;
use chrono::Utc;
use colored::*;
use dashmap::DashMap;
use futures::stream::{self, StreamExt};
use hickory_resolver::{
    config::{ResolverConfig, ResolverOpts},
    TokioAsyncResolver,
};
use indicatif::{ProgressBar, ProgressStyle};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, atomic::{AtomicU64, Ordering}};
use tokio::fs;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ReconResult {
    pub subdomain: String,
    pub ip_addresses: Vec<String>,
    pub cname: Option<String>,
    pub discovered_at: String,
    pub takeover_risk: bool,
}

// Dangling CNAME indicators (subdomain takeover targets)
const TAKEOVER_INDICATORS: &[&str] = &[
    "azurewebsites.net",
    "cloudapp.net",
    "herokuapp.com",
    "github.io",
    "fastly.net",
    "s3.amazonaws.com",
    "storage.googleapis.com",
    "netlify.app",
    "surge.sh",
    "ghost.io",
    "pantheonsite.io",
    "unbounce.com",
    "helpscoutdocs.com",
];

pub async fn run(
    domain: String,
    wordlist_path: String,
    concurrency: usize,
    output: String,
) -> Result<Vec<String>> {
    println!(
        "  {} {} → concurrency={} wordlist={}",
        "TARGET".bright_blue().bold(),
        domain.bright_white(),
        concurrency.to_string().yellow(),
        wordlist_path.dimmed()
    );

    // Load wordlist
    let wordlist_content = match fs::read_to_string(&wordlist_path).await {
        Ok(content) => content,
        Err(_) => {
            println!("{} Wordlist not found, using built-in list", "⚠".yellow());
            builtin_subdomain_list()
        }
    };

    let words: Vec<String> = wordlist_content
        .lines()
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .map(|l| format!("{}.{}", l.trim(), domain))
        .collect();

    let total = words.len() as u64;
    println!("  {} {} subdomains to test", "→".bright_blue(), total.to_string().yellow());

    // Setup DNS resolver (Google + Cloudflare)
    let mut opts = ResolverOpts::default();
    opts.timeout = std::time::Duration::from_secs(3);
    opts.attempts = 1;
    opts.num_concurrent_reqs = 8;

    let resolver = Arc::new(
        TokioAsyncResolver::tokio(ResolverConfig::google(), opts)
    );

    // Progress bar
    let pb = Arc::new(ProgressBar::new(total));
    pb.set_style(
        ProgressStyle::with_template(
            "  [{elapsed_precise}] {bar:40.blue/black} {pos}/{len} | {per_sec} | {msg}"
        )
        .unwrap()
        .progress_chars("█▓░"),
    );

    let results: Arc<DashMap<String, ReconResult>> = Arc::new(DashMap::new());
    let found_count = Arc::new(AtomicU64::new(0));

    // Dispatch concurrent DNS resolution swarm
    stream::iter(words)
        .map(|subdomain| {
            let resolver = Arc::clone(&resolver);
            let results = Arc::clone(&results);
            let pb = Arc::clone(&pb);
            let found = Arc::clone(&found_count);

            async move {
                pb.inc(1);

                match resolver.lookup_ip(subdomain.as_str()).await {
                    Ok(response) => {
                        let ips: Vec<String> = response
                            .iter()
                            .map(|ip| ip.to_string())
                            .collect();

                        if !ips.is_empty() {
                            // Check for CNAME (takeover risk detection)
                            let cname = match resolver
                                .lookup(
                                    subdomain.as_str(),
                                    hickory_resolver::proto::rr::RecordType::CNAME,
                                )
                                .await
                            {
                                Ok(lookup) => lookup
                                    .iter()
                                    .next()
                                    .map(|r| r.to_string().trim_end_matches('.').to_string()),
                                Err(_) => None,
                            };

                            let takeover_risk = check_takeover_risk(&subdomain, &cname);

                            let result = ReconResult {
                                subdomain: subdomain.clone(),
                                ip_addresses: ips,
                                cname,
                                discovered_at: Utc::now().to_rfc3339(),
                                takeover_risk,
                            };

                            let n = found.fetch_add(1, Ordering::Relaxed) + 1;
                            let risk_tag = if takeover_risk {
                                " [TAKEOVER?]".bright_red().bold().to_string()
                            } else {
                                String::new()
                            };
                            pb.set_message(format!(
                                "Found: {}{}",
                                subdomain.bright_green(),
                                risk_tag
                            ));
                            results.insert(subdomain, result);

                            if n % 10 == 0 {
                                pb.set_message(format!("{} live hosts", n.to_string().green()));
                            }
                        }
                    }
                    Err(_) => {} // NXDOMAIN or timeout — skip silently
                }
            }
        })
        .buffer_unordered(concurrency)
        .collect::<Vec<_>>()
        .await;

    pb.finish_with_message(format!(
        "Complete — {} live subdomains",
        found_count.load(Ordering::Relaxed).to_string().bright_green()
    ));

    // Collect results
    let found: Vec<ReconResult> = results
        .iter()
        .map(|entry| entry.value().clone())
        .collect();

    // Sort by subdomain name
    let mut found = found;
    found.sort_by(|a, b| a.subdomain.cmp(&b.subdomain));

    // Save output
    if let Some(parent) = std::path::Path::new(&output).parent() {
        let _ = fs::create_dir_all(parent).await;
    }
    let json = serde_json::to_string_pretty(&found)?;
    fs::write(&output, json).await?;

    let live_hosts: Vec<String> = found.iter().map(|r| r.subdomain.clone()).collect();

    println!(
        "\n  {} {} live subdomains → {}",
        "✓".green().bold(),
        live_hosts.len().to_string().bright_green(),
        output.dimmed()
    );

    // Print takeover risks
    let risks: Vec<&ReconResult> = found.iter().filter(|r| r.takeover_risk).collect();
    if !risks.is_empty() {
        println!("\n  {} {} potential subdomain takeovers:", "🎯".red(), risks.len().to_string().bright_red());
        for r in &risks {
            println!("     {} {} → {:?}", "→".red(), r.subdomain.bright_red(), r.cname);
        }
    }

    Ok(live_hosts)
}

fn check_takeover_risk(subdomain: &str, cname: &Option<String>) -> bool {
    if let Some(cn) = cname {
        TAKEOVER_INDICATORS.iter().any(|indicator| cn.contains(indicator))
    } else {
        // Heuristic: if subdomain has cloud-like patterns but no A record
        TAKEOVER_INDICATORS.iter().any(|ind| subdomain.contains(ind))
    }
}

fn builtin_subdomain_list() -> String {
    vec![
        "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
        "webdisk", "ns", "cpanel", "whm", "autodiscover", "autoconfig", "m", "imap",
        "test", "ns3", "dev", "www2", "admin", "blog", "portal", "api", "app",
        "staging", "beta", "alpha", "demo", "shop", "store", "static", "cdn",
        "media", "img", "images", "assets", "files", "upload", "uploads", "download",
        "downloads", "secure", "vpn", "remote", "git", "svn", "jenkins", "jira",
        "wiki", "docs", "support", "help", "forum", "community", "news", "status",
        "metrics", "monitoring", "grafana", "kibana", "elastic", "dashboard",
        "manage", "manage2", "cpanel2", "cpcalendars", "cpcontacts", "cpdavd",
        "mysql", "phpmyadmin", "db", "database", "redis", "cache", "queue",
        "microservice", "service", "services", "backend", "frontend", "internal",
        "intranet", "extranet", "auth", "sso", "login", "oauth", "id",
        "search", "elasticsearch", "solr", "kafka", "rabbitmq", "mq",
        "uat", "qa", "preprod", "prod", "production", "sandbox", "local",
        "mobile", "api2", "api3", "v1", "v2", "v3", "graphql", "rest",
        "webhooks", "callback", "events", "stream", "streaming",
    ]
    .join("\n")
}
