//! Jolt Atlas zkML CLI
//!
//! Command-line interface for zkSNARK proof generation and verification.
//! Called by Python server via subprocess for zkML operations.

use clap::{Parser, Subcommand};
use std::path::PathBuf;
use std::io::{self, Read};
use serde::{Serialize, Deserialize};

use jolt_zkml::{RugDetectorZKML, ZKMLError};

#[derive(Parser)]
#[command(name = "jolt_zkml_cli")]
#[command(version = "0.1.0")]
#[command(about = "Jolt Atlas zkML CLI for RugDetector", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Preprocess the ONNX model (one-time setup)
    Preprocess {
        /// Path to ONNX model file
        #[arg(long)]
        model: PathBuf,
    },

    /// Generate zkSNARK proof for inference
    Prove {
        /// Path to ONNX model file
        #[arg(long)]
        model: PathBuf,
    },

    /// Verify a zkSNARK proof
    Verify,

    /// Get version information
    Version,
}

#[derive(Deserialize)]
struct ProveInput {
    features: Vec<i32>,
}

#[derive(Serialize)]
struct ProveOutput {
    proof: String,
    output: serde_json::Value,
    verifying_key: String,
}

#[derive(Serialize)]
struct ErrorOutput {
    error: String,
}

fn main() {
    let cli = Cli::parse();

    let result = match cli.command {
        Commands::Preprocess { model } => handle_preprocess(model),
        Commands::Prove { model } => handle_prove(model),
        Commands::Verify => handle_verify(),
        Commands::Version => handle_version(),
    };

    if let Err(e) = result {
        eprintln!("{}", serde_json::to_string(&ErrorOutput {
            error: e.to_string()
        }).unwrap());
        std::process::exit(1);
    }
}

fn handle_preprocess(model: PathBuf) -> Result<(), Box<dyn std::error::Error>> {
    let mut zkml = RugDetectorZKML::new(model);
    zkml.preprocess();

    println!("{{\"status\": \"preprocessed\"}}");
    Ok(())
}

fn handle_prove(model: PathBuf) -> Result<(), Box<dyn std::error::Error>> {
    // Read features from stdin
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let prove_input: ProveInput = serde_json::from_str(&input)?;

    // Validate input
    if prove_input.features.len() != 60 {
        return Err(format!("Expected 60 features, got {}", prove_input.features.len()).into());
    }

    // Generate proof
    let mut zkml = RugDetectorZKML::new(model);
    zkml.preprocess();  // In production, this should be cached

    match zkml.prove(prove_input.features) {
        Ok(_proof_result) => {
            // Uncomment when dependencies available:
            /*
            let output = ProveOutput {
                proof: hex::encode(serialize(&proof_result.snark)),
                output: serde_json::to_value(&proof_result.output)?,
                verifying_key: hex::encode(serialize(&proof_result.verifying_key)),
            };

            println!("{}", serde_json::to_string(&output)?);
            */

            eprintln!("⚠️  Proof generation requires Jolt Atlas dependencies");
            Err("Not implemented: requires network to fetch dependencies".into())
        }
        Err(e) => Err(e.into())
    }
}

fn handle_verify() -> Result<(), Box<dyn std::error::Error>> {
    // Read verification data from stdin
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;

    // Uncomment when dependencies available:
    /*
    #[derive(Deserialize)]
    struct VerifyInput {
        proof: String,
        verifying_key: String,
        output: serde_json::Value,
    }

    let verify_input: VerifyInput = serde_json::from_str(&input)?;

    let proof_bytes = hex::decode(&verify_input.proof)?;
    let vk_bytes = hex::decode(&verify_input.verifying_key)?;
    let output_bytes = serde_json::to_vec(&verify_input.output)?;

    let is_valid = RugDetectorZKML::verify(&proof_bytes, &vk_bytes, &output_bytes)?;

    println!("{{\"valid\": {}}}", is_valid);
    */

    eprintln!("⚠️  Verification requires Jolt Atlas dependencies");
    Err("Not implemented: requires network to fetch dependencies".into())
}

fn handle_version() -> Result<(), Box<dyn std::error::Error>> {
    println!("{{");
    println!("  \"name\": \"jolt_zkml_cli\",");
    println!("  \"version\": \"0.1.0\",");
    println!("  \"description\": \"Jolt Atlas zkML CLI for RugDetector\",");
    println!("  \"status\": \"skeleton - requires dependencies\",");
    println!("  \"dependencies_required\": [");
    println!("    \"https://github.com/ICME-Lab/jolt-atlas\",");
    println!("    \"https://github.com/ICME-Lab/zkml-jolt\"");
    println!("  ]");
    println!("}}");
    Ok(())
}
