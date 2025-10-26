// POST /zkml/verify endpoint
// Verify zkML proofs for contract analysis

const express = require('express');
const router = express.Router();
const zkml = require('../services/zkmlProver');

// POST /zkml/verify - Verify a zkML proof
router.post('/', async (req, res) => {
  try {
    const { proof, features, result } = req.body;

    // Validate inputs
    if (!proof) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: proof'
      });
    }

    if (!features) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: features'
      });
    }

    if (!result) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: result (must include riskScore, riskCategory, confidence)'
      });
    }

    // Verify the proof
    console.log(`[zkML Verify] Verifying proof ${proof.proof_id?.slice(0, 16) || 'unknown'}...`);
    const verification = await zkml.verifyProof(proof, features, result);

    console.log(`[zkML Verify] Verification result: ${verification.valid ? 'VALID' : 'INVALID'}`);

    // Return verification result
    res.json({
      success: true,
      valid: verification.valid,
      proof_id: proof.proof_id,
      verified_at: verification.verified_at || new Date().toISOString(),
      reason: verification.reason
    });

  } catch (error) {
    console.error('[zkML Verify] Unexpected error:', error);
    res.status(500).json({
      success: false,
      valid: false,
      error: 'An unexpected error occurred during verification'
    });
  }
});

module.exports = router;
