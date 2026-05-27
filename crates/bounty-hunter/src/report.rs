// ============================================================
// REPORT MODULE — CORTEX-Persist Output + Terminal Summary
// ============================================================

use anyhow::Result;
use chrono::Utc;
use colored::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct BountyReport {
    pub generated_at: String,
    pub target: String,
    pub phases_run: Vec<String>,
    pub summary: ReportSummary,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReportSummary {
    pub subdomains_found: usize,
    pub live_endpoints: usize,
    pub vulnerabilities_found: usize,
    pub high_confidence: usize,
    pub medium_confidence: usize,
    pub takeover_risks: usize,
}

pub fn generate_report(target: &str, summary: ReportSummary, phases: Vec<String>) -> Result<BountyReport> {
    let report = BountyReport {
        generated_at: Utc::now().to_rfc3339(),
        target: target.to_string(),
        phases_run: phases,
        summary,
    };

    println!("\n{}", "━".repeat(62).bright_blue());
    println!("{}", "  BOUNTY HUNTER — FINAL REPORT".bright_white().bold());
    println!("{}", "━".repeat(62).bright_blue());
    println!("  Target:         {}", target.bright_white());
    println!("  Generated:      {}", report.generated_at.dimmed());
    println!("{}", "─".repeat(62).dimmed());
    println!("  Subdomains:     {}", report.summary.subdomains_found.to_string().bright_green());
    println!("  Live Endpoints: {}", report.summary.live_endpoints.to_string().bright_green());
    println!("  Vulns (HIGH):   {}", report.summary.high_confidence.to_string().bright_red());
    println!("  Vulns (MED):    {}", report.summary.medium_confidence.to_string().yellow());
    println!("  Takeover Risks: {}", report.summary.takeover_risks.to_string().bright_red());
    println!("{}", "━".repeat(62).bright_blue());

    Ok(report)
}
