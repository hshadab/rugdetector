// POST /check endpoint
// Payment-gated smart contract analysis

const express = require('express');
const router = express.Router();
const paymentService = require('../services/payment');
const rugDetector = require('../services/rugDetector');
const { getPaymentTracker } = require('../services/paymentTracker');
const x402 = require('../services/x402');
const zkml = require('../services/zkmlProver');

// Initialize payment tracker
const paymentTracker = getPaymentTracker();

// POST /check - Analyze contract for rug pull risk
router.post('/', async (req, res) => {
  try {
    // Extract request parameters
    let { payment_id, contract_address, blockchain = 'base' } = req.body;

    // Validate contract_address first
    if (!contract_address) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: contract_address'
      });
    }

    // X402: Check for X-PAYMENT header as alternative to JSON body
    const xPaymentHeader = req.get('X-PAYMENT');
    if (!payment_id && xPaymentHeader) {
      console.log('[X402] Found X-PAYMENT header, parsing...');
      const payment = x402.parsePaymentHeader(xPaymentHeader);
      if (payment && x402.isValidPaymentPayload(payment)) {
        payment_id = x402.extractTransactionHash(payment);
        console.log(`[X402] Extracted payment_id from header: ${payment_id}`);
      } else {
        console.log('[X402] Invalid X-PAYMENT header format');
      }
    }

    // Validate payment_id (after checking X-PAYMENT header)
    if (!payment_id) {
      return x402.create402Response(res, {
        amount: '0.1',
        currency: 'USDC',
        network: 'base',
        recipient: process.env.PAYMENT_ADDRESS,
        description: 'Smart contract analysis'
      });
    }

    // Validate contract address format
    const evmAddressPattern = /^0x[a-fA-F0-9]{40}$/;
    const solanaAddressPattern = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/; // Base58, typically 32-44 chars

    if (blockchain.toLowerCase() === 'solana') {
      if (!solanaAddressPattern.test(contract_address)) {
        return res.status(422).json({
          success: false,
          error: 'Invalid Solana program address format. Expected base58 encoded address (32-44 characters).'
        });
      }
    } else {
      if (!evmAddressPattern.test(contract_address)) {
        return res.status(422).json({
          success: false,
          error: 'Invalid contract address format. Expected 0x followed by 40 hex characters.'
        });
      }
    }

    // Validate blockchain
    const supportedBlockchains = ['base', 'solana'];
    if (!supportedBlockchains.includes(blockchain.toLowerCase())) {
      return res.status(422).json({
        success: false,
        error: `Unsupported blockchain. Supported: ${supportedBlockchains.join(', ')}`
      });
    }

    // Check for demo mode
    const isDemoMode = payment_id.toLowerCase().startsWith('demo_');

    // Validate payment ID format (skip for demo mode)
    if (!isDemoMode) {
      // Solana uses different transaction hash format (base58, ~88 chars)
      const evmPaymentPattern = /^(tx_)?0x[a-fA-F0-9]{64}$/;
      const solanaPaymentPattern = /^(tx_)?[1-9A-HJ-NP-Za-km-z]{87,88}$/;

      if (blockchain.toLowerCase() === 'solana') {
        if (!solanaPaymentPattern.test(payment_id)) {
          return res.status(400).json({
            success: false,
            error: 'Invalid payment_id format for Solana. Expected base58 transaction signature',
            error_code: 'INVALID_PAYMENT_ID'
          });
        }
      } else {
        if (!evmPaymentPattern.test(payment_id)) {
          return res.status(400).json({
            success: false,
            error: 'Invalid payment_id format. Expected transaction hash (0x... or tx_0x...)',
            error_code: 'INVALID_PAYMENT_ID'
          });
        }
      }
    }

    // Step 0: Check for payment replay attack (skip in demo mode)
    if (!isDemoMode) {
      console.log(`[Check] Checking payment replay for: ${payment_id}`);
      if (paymentTracker.isUsed(payment_id)) {
        console.log(`[Check] ⚠️ REPLAY ATTACK DETECTED: ${payment_id}`);
        return x402.create402Response(res, {
          amount: '0.1',
          currency: 'USDC',
          network: 'base',
          recipient: process.env.PAYMENT_ADDRESS,
          description: 'Smart contract analysis (payment already used)'
        });
      }
    }

    // Step 1: Verify payment (skip in demo mode)
    if (isDemoMode) {
      console.log(`[Check] 🎭 DEMO MODE: Skipping payment verification for ${payment_id}`);
    } else {
      console.log(`[Check] Verifying payment: ${payment_id}`);
      try {
        const paymentVerified = await paymentService.verifyPayment(payment_id);

        if (!paymentVerified.verified) {
          return x402.create402Response(res, {
            amount: '0.1',
            currency: 'USDC',
            network: 'base',
            recipient: process.env.PAYMENT_ADDRESS,
            description: 'Smart contract analysis (payment verification failed)'
          });
        }

        console.log(`[Check] Payment verified: ${paymentVerified.amount} USDC units`);

        // Mark payment as used AFTER successful verification
        const marked = paymentTracker.markUsed(payment_id, {
          contract_address,
          blockchain,
          timestamp: new Date().toISOString(),
          amount: paymentVerified.amount
        });

        if (!marked) {
          // This shouldn't happen since we checked above, but handle it anyway
          console.error('[Check] Failed to mark payment as used (race condition?)');
          return x402.create402Response(res, {
            amount: '0.1',
            currency: 'USDC',
            network: 'base',
            recipient: process.env.PAYMENT_ADDRESS,
            description: 'Smart contract analysis (payment already used - race condition)'
          });
        }

        console.log(`[Check] ✅ Payment marked as used: ${payment_id}`);

      } catch (paymentError) {
        console.error('[Check] Payment verification error:', paymentError.message);
        return x402.create402Response(res, {
          amount: '0.1',
          currency: 'USDC',
          network: 'base',
          recipient: process.env.PAYMENT_ADDRESS,
          description: `Smart contract analysis (error: ${paymentError.message})`
        });
      }
    }

    // Step 2: Extract features from contract
    console.log(`[Check] Extracting features from ${contract_address} on ${blockchain}`);
    let features, zkmlFeatures;
    try {
      // Use zkML model if enabled
      if (rugDetector.USE_ZKML_MODEL) {
        console.log(`[Check] Using zkML model (18 features)`);
        zkmlFeatures = await rugDetector.extractZkmlFeatures(contract_address, blockchain);
        console.log(`[Check] Extracted ${zkmlFeatures.length} zkML features`);
        features = zkmlFeatures;  // For backward compatibility
      } else {
        features = await rugDetector.extractFeatures(contract_address, blockchain);
        console.log(`[Check] Extracted ${Object.keys(features).length} features`);
      }
    } catch (extractError) {
      console.error('[Check] Feature extraction error:', extractError.message);
      return res.status(500).json({
        success: false,
        error: `Feature extraction failed: ${extractError.message}`
      });
    }

    // Step 3: Analyze contract using ONNX model
    console.log(`[Check] Running ONNX inference`);
    let analysis;
    try {
      if (rugDetector.USE_ZKML_MODEL) {
        analysis = await rugDetector.analyzeContractZkml(zkmlFeatures);
      } else {
        analysis = await rugDetector.analyzeContract(features);
      }
      console.log(`[Check] Analysis complete: ${analysis.riskCategory} risk (score: ${analysis.riskScore})`);
    } catch (analysisError) {
      console.error('[Check] Analysis error:', analysisError.message);
      return res.status(500).json({
        success: false,
        error: `Analysis failed: ${analysisError.message}`
      });
    }

    // Step 4: Generate recommendation
    let recommendation;
    if (analysis.riskCategory === 'high') {
      recommendation = 'High risk detected. Avoid investing. Multiple red flags identified.';
    } else if (analysis.riskCategory === 'medium') {
      recommendation = 'Medium risk detected. Proceed with caution and conduct thorough research.';
    } else {
      recommendation = 'Low risk detected. Contract appears relatively safe, but always DYOR.';
    }

    // Step 5: Generate zkML proof
    console.log(`[Check] Generating zkML proof`);
    let zkmlProof;
    try {
      zkmlProof = await zkml.generateProof(features, analysis);
      console.log(`[Check] zkML proof generated: ${zkmlProof.proof_id.slice(0, 16)}...`);
    } catch (proofError) {
      console.error('[Check] zkML proof generation failed:', proofError.message);
      // Continue without proof if generation fails
      zkmlProof = {
        proof_id: 'unavailable',
        protocol: 'jolt-atlas-v1',
        verifiable: false,
        verified: false,
        error: 'Proof generation failed'
      };
    }

    // Step 6: Verify zkML proof locally
    let verification = { valid: false, reason: 'Not verified' };
    if (zkmlProof && zkmlProof.proof_id !== 'unavailable' && zkmlProof.proof_id !== 'error') {
      console.log(`[Check] Verifying zkML proof ${zkmlProof.proof_id.slice(0, 16)}...`);
      try {
        verification = await zkml.verifyProof(zkmlProof, features, analysis);
        console.log(`[Check] Proof verification result: ${verification.valid ? '✅ VALID' : '❌ INVALID'}`);

        // Add verification result to proof object
        zkmlProof.verified = verification.valid;
        zkmlProof.verified_at = verification.verified_at;

        if (!verification.valid) {
          console.warn(`[Check] ⚠️ WARNING: Proof verification failed: ${verification.reason}`);
          zkmlProof.verification_warning = verification.reason;
        }
      } catch (verifyError) {
        console.error('[Check] Proof verification error:', verifyError.message);
        zkmlProof.verified = false;
        zkmlProof.verification_error = verifyError.message;
      }
    } else {
      console.log(`[Check] Skipping verification - no valid proof to verify`);
      zkmlProof.verified = false;
    }

    // Return successful response with zkML proof
    res.json({
      success: true,
      data: {
        contract_address,
        blockchain,
        riskScore: analysis.riskScore,
        riskCategory: analysis.riskCategory,
        confidence: analysis.confidence,
        features: features,
        recommendation: recommendation,
        analysis_timestamp: new Date().toISOString(),
        zkml: zkmlProof
      }
    });

  } catch (error) {
    console.error('[Check] Unexpected error:', error);
    res.status(500).json({
      success: false,
      error: 'An unexpected error occurred during analysis'
    });
  }
});

module.exports = router;
