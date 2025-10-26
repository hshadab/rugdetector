// zkML Proof Generation and Verification using Jolt-Atlas
// Full Rust prover implementation - NO fallback approaches

const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

const MODEL_PATH = path.join(__dirname, '../../model/zkml_rugdetector.onnx');  // Use zkML model
const PROVER_BINARY = path.join(__dirname, '../../zkml-jolt-atlas/target/release/zkml-jolt-core');
const TEMP_DIR = path.join(__dirname, '../../.zkml_temp');

// Ensure temp directory exists
async function ensureTempDir() {
  try {
    await fs.mkdir(TEMP_DIR, { recursive: true });
  } catch (error) {
    console.error('[zkML] Failed to create temp directory:', error);
  }
}

/**
 * Generate zkML proof for ML inference using Jolt-Atlas
 * Creates full cryptographic proof via Rust prover
 *
 * @param {Array|Object} features - Input features (18 element array or object with values)
 * @param {Object} result - Inference result (riskScore, probabilities, etc)
 * @returns {Promise<Object>} zkML proof object
 */
async function generateProof(features, result) {
  try {
    await ensureTempDir();

    const timestamp = Math.floor(Date.now() / 1000);
    const proofId = crypto.randomBytes(16).toString('hex');

    // Prepare input data - convert features object/array to array
    const featureArray = Array.isArray(features) ? features : Object.values(features);

    // Create temporary input file
    const inputPath = path.join(TEMP_DIR, `input_${proofId}.json`);
    const outputPath = path.join(TEMP_DIR, `proof_${proofId}.json`);

    await fs.writeFile(inputPath, JSON.stringify(featureArray));

    console.log(`[zkML] Generating Jolt-Atlas proof ${proofId.slice(0, 16)}...`);
    console.log(`[zkML] Input: ${featureArray.length} features`);
    console.log(`[zkML] Model: ${MODEL_PATH}`);

    // Call Rust prover
    const proof = await new Promise((resolve, reject) => {
      const prover = spawn(PROVER_BINARY, [
        'prove',
        '--model', MODEL_PATH,
        '--input', inputPath,
        '--shape', `1,${featureArray.length}`,
        '--output', outputPath
      ]);

      let stdout = '';
      let stderr = '';

      prover.stdout.on('data', (data) => {
        stdout += data.toString();
        console.log(`[zkML Prover] ${data.toString().trim()}`);
      });

      prover.stderr.on('data', (data) => {
        stderr += data.toString();
        console.error(`[zkML Prover Error] ${data.toString().trim()}`);
      });

      prover.on('close', async (code) => {
        if (code !== 0) {
          reject(new Error(`Prover exited with code ${code}: ${stderr}`));
          return;
        }

        try {
          // Read the proof file
          const proofJson = await fs.readFile(outputPath, 'utf8');
          const proofData = JSON.parse(proofJson);

          // Clean up temp files
          await fs.unlink(inputPath).catch(() => {});
          await fs.unlink(outputPath).catch(() => {});

          resolve(proofData);
        } catch (error) {
          reject(error);
        }
      });

      // Timeout after 2 minutes
      setTimeout(() => {
        prover.kill();
        reject(new Error('Proof generation timed out after 2 minutes'));
      }, 120000);
    });

    console.log(`[zkML] Jolt-Atlas proof generated: ${proof.proof_id?.slice(0, 16)}...`);

    // Add additional metadata
    proof.proof_size_bytes = JSON.stringify(proof).length;
    proof.generated_at = new Date(timestamp * 1000).toISOString();

    return proof;

  } catch (error) {
    console.error(`[zkML] Proof generation failed:`, error);

    // Return error proof (do NOT fall back to SHA-256)
    return {
      proof_id: 'error',
      protocol: 'jolt-atlas-v1',
      verifiable: false,
      zkml_enabled: false,
      error: error.message,
      note: 'Proof generation failed - no fallback available'
    };
  }
}

/**
 * Verify zkML proof using Jolt-Atlas
 * Calls Rust verifier
 *
 * @param {Object} proof - The proof to verify
 * @param {Object} features - Original input features
 * @param {Object} result - Original inference result
 * @returns {Promise<{valid: boolean, reason?: string}>}
 */
async function verifyProof(proof, features, result) {
  try {
    await ensureTempDir();

    const proofId = proof.proof_id || 'unknown';
    const proofPath = path.join(TEMP_DIR, `verify_${proofId}_${Date.now()}.json`);

    // Write proof to temp file
    await fs.writeFile(proofPath, JSON.stringify(proof));

    console.log(`[zkML] Verifying proof ${proofId.slice(0, 16)}...`);

    // Call Rust verifier
    const valid = await new Promise((resolve, reject) => {
      const verifier = spawn(PROVER_BINARY, [
        'verify',
        '--proof', proofPath
      ]);

      let stdout = '';
      let stderr = '';

      verifier.stdout.on('data', (data) => {
        stdout += data.toString();
        console.log(`[zkML Verifier] ${data.toString().trim()}`);
      });

      verifier.stderr.on('data', (data) => {
        stderr += data.toString();
        console.error(`[zkML Verifier Error] ${data.toString().trim()}`);
      });

      verifier.on('close', async (code) => {
        // Clean up temp file
        await fs.unlink(proofPath).catch(() => {});

        // Exit code 0 = valid, 1 = invalid, other = error
        if (code === 0) {
          resolve(true);
        } else if (code === 1) {
          resolve(false);
        } else {
          reject(new Error(`Verifier exited with code ${code}: ${stderr}`));
        }
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        verifier.kill();
        reject(new Error('Proof verification timed out after 30 seconds'));
      }, 30000);
    });

    console.log(`[zkML] Proof verification result: ${valid ? 'VALID' : 'INVALID'}`);

    return {
      valid: valid,
      verified_at: new Date().toISOString(),
      reason: valid ? undefined : 'Proof verification failed'
    };

  } catch (error) {
    console.error(`[zkML] Verification failed:`, error);
    return {
      valid: false,
      reason: `Verification error: ${error.message}`
    };
  }
}

module.exports = {
  generateProof,
  verifyProof
};
