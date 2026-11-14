// crates/actrun-trace/src/main.rs
use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::path::PathBuf;

/// ActRun Trace Analyzer
/// Analyse un journal JSONL d'événements ActRun et calcule des métriques de coordination.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Fichier JSONL d'événements à analyser
    input: PathBuf,

    /// Fichier de sortie (optionnel, sinon stdout)
    #[arg(short, long)]
    output: Option<PathBuf>,

    /// Sortie au format JSON
    #[arg(long)]
    json: bool,
}

/// Représentation d'un événement ActRun (doit correspondre au schéma Python)
#[derive(Debug, Deserialize, Clone)]
struct Event {
    event_id: String,
    timestamp: String,
    agent_id: String,
    action: String,
    #[serde(default)]
    payload: serde_json::Value,
    #[serde(default)]
    metadata: Option<serde_json::Value>,
}

/// Métriques agrégées
#[derive(Debug, Serialize, Default)]
struct Metrics {
    total_events: usize,
    events_by_action: HashMap<String, usize>,
    events_by_agent: HashMap<String, usize>,
    
    // Métriques spécifiques
    total_commits: usize,
    total_branches: usize,
    total_conflicts: usize,          // Conflits détectés (dans les payloads)
    total_leases_acquired: usize,
    total_leases_released: usize,
    
    // Coordination overhead
    conflict_rate: f64,              // conflits / tentatives de commit
    coordination_events_ratio: f64,  // (branches + leases) / total
    
    // Temporel
    first_event: Option<String>,
    last_event: Option<String>,
    duration_seconds: Option<f64>,
}

fn main() -> Result<()> {
    let args = Args::parse();
    
    // 1. Lire le fichier JSONL
    let file = File::open(&args.input)
        .with_context(|| format!("Impossible d'ouvrir {:?}", args.input))?;
    let reader = BufReader::new(file);
    
    // 2. Parser et agréger
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
        
        // Comptages généraux
        metrics.total_events += 1;
        *metrics.events_by_action.entry(event.action.clone()).or_insert(0) += 1;
        *metrics.events_by_agent.entry(event.agent_id.clone()).or_insert(0) += 1;
        
        // Parser le timestamp
        if let Ok(ts) = DateTime::parse_from_rfc3339(&event.timestamp) {
            timestamps.push(ts.with_timezone(&Utc));
        }
        
        // Métriques spécifiques selon le type d'action
        match event.action.as_str() {
            "workspace.commit" => {
                metrics.total_commits += 1;
                // Détecter si c'est un commit en conflit (payload contient "conflict" ou "failed")
                if let Some(payload_str) = event.payload.as_object() {
                    if payload_str.contains_key("conflict") {
                        metrics.total_conflicts += 1;
                    }
                }
            }
            "workspace.branch" => {
                metrics.total_branches += 1;
            }
            "lease.acquire" => {
                metrics.total_leases_acquired += 1;
            }
            "lease.release" => {
                metrics.total_leases_released += 1;
            }
            "coordination.conflict" => {
                // Événement explicite de conflit (si on en ajoute plus tard)
                metrics.total_conflicts += 1;
            }
            _ => {}
        }
    }
    
    // 3. Calculer les métriques dérivées
    metrics.conflict_rate = if metrics.total_commits > 0 {
        metrics.total_conflicts as f64 / metrics.total_commits as f64
    } else {
        0.0
    };
    
    let coordination_events = metrics.total_branches + metrics.total_leases_acquired;
    metrics.coordination_events_ratio = if metrics.total_events > 0 {
        coordination_events as f64 / metrics.total_events as f64
    } else {
        0.0
    };
    
    if let (Some(first), Some(last)) = (timestamps.iter().min(), timestamps.iter().max()) {
        metrics.first_event = Some(first.to_rfc3339());
        metrics.last_event = Some(last.to_rfc3339());
        metrics.duration_seconds = Some((last - first).num_milliseconds() as f64 / 1000.0);
    }
    
    // 4. Sortir le résultat
    let output: String = if args.json {
        serde_json::to_string_pretty(&metrics)?
    } else {
        format_text_report(&metrics)
    };
    
    match args.output {
        Some(path) => {
            let mut file = File::create(&path)?;
            file.write_all(output.as_bytes())?;
            println!("✅ Rapport écrit dans {:?}", path);
        }
        None => {
            println!("{}", output);
        }
    }
    
    Ok(())
}

/// Formate un rapport texte lisible
fn format_text_report(m: &Metrics) -> String {
    let mut s = String::new();
    
    s.push_str("╔══════════════════════════════════════════════════════════╗\n");
    s.push_str("║          ACTRUN TRACE ANALYSIS REPORT                  ║\n");
    s.push_str("╚══════════════════════════════════════════════════════════╝\n\n");
    
    s.push_str(&format!("📊 Total événements : {}\n", m.total_events));
    
    if let (Some(first), Some(last), Some(duration)) = (&m.first_event, &m.last_event, m.duration_seconds) {
        s.push_str(&format!("⏱️  Durée totale     : {:.2}s\n", duration));
        s.push_str(&format!("   De {} à {}\n\n", 
            &first[11..19], &last[11..19]));
    }
    
    s.push_str("📈 Événements par action :\n");
    let mut actions: Vec<_> = m.events_by_action.iter().collect();
    actions.sort_by(|a, b| b.1.cmp(a.1));
    for (action, count) in actions {
        s.push_str(&format!("   • {:<25} : {}\n", action, count));
    }
    
    s.push_str("\n👥 Événements par agent :\n");
    let mut agents: Vec<_> = m.events_by_agent.iter().collect();
    agents.sort_by(|a, b| b.1.cmp(a.1));
    for (agent, count) in agents {
        s.push_str(&format!("   • {:<25} : {}\n", agent, count));
    }
    
    s.push_str("\n🎯 Métriques de coordination :\n");
    s.push_str(&format!("   • Branches créées      : {}\n", m.total_branches));
    s.push_str(&format!("   • Commits réussis      : {}\n", m.total_commits));
    s.push_str(&format!("   • Conflits détectés    : {}\n", m.total_conflicts));
    s.push_str(&format!("   • Leases acquis        : {}\n", m.total_leases_acquired));
    s.push_str(&format!("   • Leases libérés       : {}\n", m.total_leases_released));
    
    s.push_str("\n📉 Indicateurs clés :\n");
    s.push_str(&format!("   • Taux de conflit      : {:.1}%\n", m.conflict_rate * 100.0));
    s.push_str(&format!("   • Overhead coordination: {:.1}%\n", m.coordination_events_ratio * 100.0));
    
    // Interprétation
    s.push_str("\n💡 Interprétation :\n");
    if m.conflict_rate > 0.3 {
        s.push_str("   ⚠️  Taux de conflit élevé (>30%). Les agents se marchent souvent dessus.\n");
        s.push_str("      → Envisage d'utiliser plus de leases pour prévenir les conflits.\n");
    } else if m.conflict_rate > 0.0 {
        s.push_str("   ✅ Taux de conflit acceptable. Le système détecte et bloque les collisions.\n");
    } else {
        s.push_str("   ✅ Aucun conflit détecté. Coordination très efficace.\n");
    }
    
    if m.coordination_events_ratio > 0.6 {
        s.push_str("   ⚠️  Overhead de coordination élevé. Beaucoup d'événements sont de la gestion.\n");
    }
    
    s.push_str("\n");
    s
}
