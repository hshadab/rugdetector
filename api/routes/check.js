// POST /check endpoint
// Payment-gated smart contract analysis

const express = require('express');
const router = express.Router();
const paymentService = require('../services/payment');
const rugDetector = require('../services/rugDetector');
const { getPaymentTracker } = require('../services/paymentTracker');

// Initialize payment tracker
const paymentTracker = getPaymentTracker();

// POST /check - Analyze contract for rug pull risk
router.post('/', async (req, res) => {
  try {
    // Extract request parameters
    const { payment_id, contract_address, blockchain = 'ethereum' } = req.body;

    // Validate required fields
    if (!payment_id) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: payment_id'
      });
    }

    if (!contract_address) {
      return res.status(400).json({
        success: false,
        error: 'Missing required field: contract_address'
      });
    }

    // Validate contract address format
    const addressPattern = /^0x[a-fA-F0-9]{40}$/;
    if (!addressPattern.test(contract_address)) {
      return res.status(422).json({
        success: false,
        error: 'Invalid contract address format. Expected 0x followed by 40 hex characters.'
      });
    }

    // Validate blockchain
    const supportedBlockchains = ['ethereum', 'bsc', 'polygon'];
    if (!supportedBlockchains.includes(blockchain.toLowerCase())) {
      return res.status(422).json({
        success: false,
        error: `Unsupported blockchain. Supported: ${supportedBlockchains.join(', ')}`
      });
    }

    // Validate payment ID format
    const paymentIdPattern = /^(tx_)?0x[a-fA-F0-9]{64}$/;
    if (!paymentIdPattern.test(payment_id)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid payment_id format. Expected transaction hash (0x... or tx_0x...)',
        error_code: 'INVALID_PAYMENT_ID'
      });
    }

    // Step 0: Check for payment replay attack
    console.log(`[Check] Checking payment replay for: ${payment_id}`);
    if (paymentTracker.isUsed(payment_id)) {
      console.log(`[Check] ⚠️ REPLAY ATTACK DETECTED: ${payment_id}`);
      return res.status(402).json({
        success: false,
        error: 'Payment ID has already been used. Each payment can only be used for one analysis.',
        error_code: 'PAYMENT_ALREADY_USED',
        hint: 'Please make a new payment for another analysis.'
      });
    }

    // Step 1: Verify payment
    console.log(`[Check] Verifying payment: ${payment_id}`);
    try {
      const paymentVerified = await paymentService.verifyPayment(payment_id);

      if (!paymentVerified.verified) {
        return res.status(402).json({
          success: false,
          error: 'Payment verification failed. Please ensure you sent 0.1 USDC to the service address.'
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
        return res.status(402).json({
          success: false,
          error: 'Payment ID has already been used.',
          error_code: 'PAYMENT_ALREADY_USED'
        });
      }

      console.log(`[Check] ✅ Payment marked as used: ${payment_id}`);

    } catch (paymentError) {
      console.error('[Check] Payment verification error:', paymentError.message);
      return res.status(402).json({
        success: false,
        error: `Payment verification failed: ${paymentError.message}`,
        error_code: 'PAYMENT_VERIFICATION_FAILED'
      });
    }

    // Step 2: Extract features from contract
    console.log(`[Check] Extracting features from ${contract_address} on ${blockchain}`);
    let features;
    try {
      features = await rugDetector.extractFeatures(contract_address, blockchain);
      console.log(`[Check] Extracted ${Object.keys(features).length} features`);
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
      analysis = await rugDetector.analyzeContract(features);
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

    // Return successful response
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
        analysis_timestamp: new Date().toISOString()
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
