use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use clap::Parser;
use serde::Deserialize;
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Fichier JSONL d'entrée contenant les événements ActRun
    input: String,
}

fn default_schema_version() -> String {
    // Backward compatibility with JSONL records written before schema_version existed.
    "1.0.0".to_owned()
}

#[derive(Deserialize, Debug)]
#[allow(dead_code)]
struct Event {
    #[serde(default = "default_schema_version")]
    schema_version: String,
    event_id: String,
    timestamp: String,
    agent_id: String,
    action: String,
    payload: serde_json::Value,
    #[serde(default)]
    metadata: Option<serde_json::Value>,
}

#[derive(Default)]
struct Metrics {
    total_events: usize,
    events_by_action: HashMap<String, usize>,
    events_by_agent: HashMap<String, usize>,
    total_commits: usize,
    total_branches: usize,
    total_conflicts: usize,
    total_leases_acquired: usize,
    total_leases_released: usize,
    conflict_rate: f64,
    coordination_events_ratio: f64,
    first_event: Option<String>,
    last_event: Option<String>,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let file =
        File::open(&args.input).with_context(|| format!("Impossible d'ouvrir {:?}", args.input))?;
    let reader = BufReader::new(file);

    let mut metrics = Metrics::default();
    let mut timestamps: Vec<DateTime<Utc>> = Vec::new();

    for (line_num, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("Erreur de lecture ligne {}", line_num + 1))?;
        let line = line.trim();
        if line.is_empty() {
            continue;
        }

        let event: Event = serde_json::from_str(line)
            .with_context(|| format!("Erreur de parsing JSON ligne {}", line_num + 1))?;

        metrics.total_events += 1;
        *metrics
            .events_by_action
            .entry(event.action.clone())
            .or_insert(0) += 1;
        *metrics
            .events_by_agent
            .entry(event.agent_id.clone())
            .or_insert(0) += 1;

        if let Ok(ts) = DateTime::parse_from_rfc3339(&event.timestamp) {
            timestamps.push(ts.with_timezone(&Utc));
        }

        match event.action.as_str() {
            "workspace.commit" => metrics.total_commits += 1,
            "workspace.branch" => metrics.total_branches += 1,
            "coordination.conflict" | "merge.conflict_detected" => {
                metrics.total_conflicts += 1;
            }
            "lease.acquire" => metrics.total_leases_acquired += 1,
            "lease.release" => metrics.total_leases_released += 1,
            _ => {}
        }
    }

    // A conflict event represents a rejected commit attempt. Include it in the
    // denominator instead of dividing conflicts by successful commits only.
    let commit_attempts = metrics.total_commits + metrics.total_conflicts;
    metrics.conflict_rate = if commit_attempts > 0 {
        metrics.total_conflicts as f64 / commit_attempts as f64 * 100.0
    } else {
        0.0
    };

    let coordination_events = metrics.total_branches + metrics.total_leases_acquired;
    metrics.coordination_events_ratio = if metrics.total_events > 0 {
        coordination_events as f64 / metrics.total_events as f64 * 100.0
    } else {
        0.0
    };

    if !timestamps.is_empty() {
        timestamps.sort();
        metrics.first_event = timestamps.first().map(|ts| ts.to_rfc3339());
        metrics.last_event = timestamps.last().map(|ts| ts.to_rfc3339());
    }

    println!("{}", generate_report(&metrics));
    Ok(())
}

fn generate_report(metrics: &Metrics) -> String {
    let mut s = String::new();
    s.push_str("📊 Rapport d'analyse ActRun\n");
    s.push_str("========================\n");
    s.push_str(&format!("Événements totaux : {}\n", metrics.total_events));
    s.push_str(&format!("Agents uniques    : {}\n", metrics.events_by_agent.len()));
    s.push_str(&format!("Commits réussis   : {}\n", metrics.total_commits));
    s.push_str(&format!("Branches créées   : {}\n", metrics.total_branches));
    s.push_str(&format!("Conflits détectés : {}\n", metrics.total_conflicts));
    s.push_str(&format!("Taux de conflit   : {:.2}%\n", metrics.conflict_rate));
    s.push_str(&format!("Overhead coord.   : {:.2}%\n", metrics.coordination_events_ratio));

    if let (Some(first), Some(last)) = (&metrics.first_event, &metrics.last_event) {
        s.push_str(&format!("Période           : {} -> {}\n", first, last));
    }

    if metrics.coordination_events_ratio > 50.0 {
        s.push_str("\n⚠️ Overhead de coordination élevé.\n");
    }

    s.push('\n');
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_current_python_event_shape() {
        let json = r#"{"schema_version":"1.0.0","event_id":"00000000-0000-0000-0000-000000000001","timestamp":"2026-11-15T10:00:00+00:00","agent_id":"agent-a","action":"workspace.commit","payload":{"version_id":"v1"},"metadata":null}"#;
        let event: Event = serde_json::from_str(json).expect("current event should parse");
        assert_eq!(event.schema_version, "1.0.0");
        assert_eq!(event.action, "workspace.commit");
    }

    #[test]
    fn accepts_legacy_event_without_schema_version() {
        let json = r#"{"event_id":"00000000-0000-0000-0000-000000000001","timestamp":"2026-11-15T10:00:00+00:00","agent_id":"agent-a","action":"workspace.commit","payload":{}}"#;
        let event: Event = serde_json::from_str(json).expect("legacy event should parse");
        assert_eq!(event.schema_version, "1.0.0");
    }
}
