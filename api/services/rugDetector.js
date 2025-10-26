// Rug Detector Service
// ONNX model inference for smart contract risk analysis

const { spawn } = require('child_process');
const path = require('path');
const onnx = require('onnxruntime-node');

// Configuration
const PYTHON_PATH = process.env.PYTHON_PATH || 'python3';
const FEATURE_EXTRACTOR_PATH = path.join(__dirname, '../../model/extract_features.py');
const MODEL_PATH = path.join(__dirname, '../../model/rugdetector_v1.onnx');
const ZKML_MODEL_PATH = path.join(__dirname, '../../model/zkml_rugdetector.onnx');
const ZKML_SCALER_PATH = path.join(__dirname, '../../model/zkml_rugdetector_scaler.pkl');

// Use zkML model for proof generation
const USE_ZKML_MODEL = process.env.USE_ZKML_MODEL !== 'false';

// Cache for ONNX session
let cachedSession = null;

/**
 * Extract blockchain features from smart contract
 * Calls Python script as subprocess
 * @param {string} contractAddress - Contract address (0x...)
 * @param {string} blockchain - Blockchain name (ethereum, bsc, polygon)
 * @returns {Promise<Object>} - 60 features as key-value pairs
 */
async function extractFeatures(contractAddress, blockchain) {
  return new Promise((resolve, reject) => {
    console.log(`[RugDetector] Spawning Python process for feature extraction`);

    // Spawn Python subprocess
    const pythonProcess = spawn(PYTHON_PATH, [
      FEATURE_EXTRACTOR_PATH,
      contractAddress,
      blockchain
    ]);

    let stdout = '';
    let stderr = '';

    // Collect stdout
    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    // Collect stderr
    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
      console.error(`[RugDetector] Python stderr: ${data}`);
    });

    // Handle process completion
    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`[RugDetector] Python process exited with code ${code}`);
        console.error(`[RugDetector] stderr: ${stderr}`);
        return reject(new Error(`Feature extraction failed with exit code ${code}`));
      }

      try {
        // Parse JSON output
        const features = JSON.parse(stdout);
        console.log(`[RugDetector] Successfully extracted ${Object.keys(features).length} features`);
        resolve(features);
      } catch (parseError) {
        console.error(`[RugDetector] Failed to parse Python output:`, stdout);
        reject(new Error('Failed to parse feature extraction output'));
      }
    });

    // Handle process errors
    pythonProcess.on('error', (error) => {
      console.error(`[RugDetector] Failed to spawn Python process:`, error);
      reject(new Error(`Failed to run feature extraction: ${error.message}`));
    });

    // Set timeout (30 seconds)
    setTimeout(() => {
      pythonProcess.kill();
      reject(new Error('Feature extraction timed out after 30 seconds'));
    }, 30000);
  });
}

/**
 * Load ONNX model session (cached)
 * @returns {Promise<InferenceSession>}
 */
async function loadModel() {
  if (cachedSession) {
    return cachedSession;
  }

  console.log(`[RugDetector] Loading ONNX model from ${MODEL_PATH}`);
  try {
    cachedSession = await onnx.InferenceSession.create(MODEL_PATH);
    console.log(`[RugDetector] Model loaded successfully`);
    return cachedSession;
  } catch (error) {
    console.error(`[RugDetector] Failed to load ONNX model:`, error);
    throw new Error(`Failed to load ML model: ${error.message}`);
  }
}

/**
 * Analyze contract using ONNX model
 * @param {Object} features - 60 features extracted from contract
 * @returns {Promise<{riskScore: number, riskCategory: string, confidence: number, probabilities?: {low:number, medium:number, high:number}}>} 
 */
async function analyzeContract(features) {
  try {
    // Load model
    const session = await loadModel();

    // Convert features object to array (must match training order)
    const featureArray = convertFeaturesToArray(features);

    // Create input tensor
    const inputTensor = new onnx.Tensor('float32', Float32Array.from(featureArray), [1, 60]);

    console.log(`[RugDetector] Running ONNX inference`);

    // Try Node inference. If model outputs include non-tensor types (ZipMap),
    // onnxruntime-node will throw. In that case, fallback to Python inference.
    // Run and pick probability tensor. Prefer a float tensor output; avoid non-tensor outputs.
    const results = await session.run({ float_input: inputTensor });

    const names = session.outputNames || [];
    let probName = null;
    // common names
    if (names.includes('output_probability')) probName = 'output_probability';
    else if (names.includes('probabilities')) probName = 'probabilities';
    else {
      // find first float tensor output by inspecting result types
      for (const n of names) {
        const v = results[n];
        if (v && v.data && (v.data instanceof Float32Array || v.data instanceof Float64Array)) {
          probName = n; break;
        }
      }
    }

    if (!probName) {
      throw new Error('No float probability tensor found in ONNX outputs: ' + JSON.stringify(names));
    }

    const probTensor = results[probName];
    const probabilities = Array.from(probTensor.data);

    console.log(`[RugDetector] Model output classes: ${probabilities.length}`);

    // Handle both 2-class (low, high) and 3-class (low, medium, high) models
    let lowRiskProb, mediumRiskProb, highRiskProb;

    if (probabilities.length === 2) {
      // 2-class model: [low_risk_prob, high_risk_prob]
      lowRiskProb = probabilities[0];
      mediumRiskProb = 0; // No medium class
      highRiskProb = probabilities[1];
      console.log(`[RugDetector] 2-class model - Low: ${lowRiskProb.toFixed(3)}, High: ${highRiskProb.toFixed(3)}`);
    } else {
      // 3-class model: [low_risk_prob, medium_risk_prob, high_risk_prob]
      lowRiskProb = probabilities[0];
      mediumRiskProb = probabilities[1] || 0;
      highRiskProb = probabilities[2] || 0;
      console.log(`[RugDetector] 3-class model - Low: ${lowRiskProb.toFixed(3)}, Medium: ${mediumRiskProb.toFixed(3)}, High: ${highRiskProb.toFixed(3)}`);
    }

    // Determine risk category and score
    let riskCategory;
    let riskScore;
    let confidence;

    if (highRiskProb > 0.6) {
      riskCategory = 'high';
      riskScore = 0.6 + (highRiskProb - 0.6) * 0.4 / 0.4; // Map to 0.6-1.0
      confidence = highRiskProb;
    } else if (mediumRiskProb > 0.5) {
      riskCategory = 'medium';
      riskScore = 0.3 + (mediumRiskProb - 0.5) * 0.3 / 0.5; // Map to 0.3-0.6
      confidence = mediumRiskProb;
    } else {
      riskCategory = 'low';
      riskScore = lowRiskProb * 0.3; // Map to 0.0-0.3
      confidence = lowRiskProb;
    }

    return {
      riskScore: Math.round(riskScore * 100) / 100, // Round to 2 decimals
      riskCategory,
      confidence: Math.round(confidence * 100) / 100,
      probabilities: {
        low: Math.round(lowRiskProb * 100) / 100,
        medium: Math.round(mediumRiskProb * 100) / 100,
        high: Math.round(highRiskProb * 100) / 100
      }
    };

  } catch (error) {
    console.error(`[RugDetector] Analysis failed:`, error);
    throw error;
  }
}

// Python fallback removed after confirming ONNX model outputs tensor probabilities

/**
 * Convert features object to ordered array for ONNX model
 * Must match the order used during training
 * @param {Object} features - Features object
 * @returns {Array<number>} - 60-element array
 */
function convertFeaturesToArray(features) {
  // Define feature order (must match training)
  const featureOrder = [
    // Ownership features (10)
    'hasOwnershipTransfer', 'hasRenounceOwnership', 'ownerBalance', 'ownerTransactionCount',
    'multipleOwners', 'ownershipChangedRecently', 'ownerContractAge', 'ownerIsContract',
    'ownerBlacklisted', 'ownerVerified',

    // Liquidity features (12)
    'hasLiquidityLock', 'liquidityPoolSize', 'liquidityRatio', 'hasUniswapV2',
    'hasPancakeSwap', 'liquidityLockedDays', 'liquidityProvidedByOwner', 'multiplePoolsExist',
    'poolCreatedRecently', 'lowLiquidityWarning', 'rugpullHistoryOnDEX', 'slippageTooHigh',

    // Holder analysis (10)
    'holderCount', 'holderConcentration', 'top10HoldersPercent', 'averageHoldingTime',
    'suspiciousHolderPatterns', 'whaleCount', 'holderGrowthRate', 'dormantHolders',
    'newHoldersSpiking', 'sellingPressure',

    // Contract code features (15)
    'hasHiddenMint', 'hasPausableTransfers', 'hasBlacklist', 'hasWhitelist',
    'hasTimelocks', 'complexityScore', 'hasProxyPattern', 'isUpgradeable',
    'hasExternalCalls', 'hasSelfDestruct', 'hasDelegateCall', 'hasInlineAssembly',
    'verifiedContract', 'auditedByFirm', 'openSourceCode',

    // Transaction patterns (8)
    'avgDailyTransactions', 'transactionVelocity', 'uniqueInteractors', 'suspiciousPatterns',
    'highFailureRate', 'gasOptimized', 'flashloanInteractions', 'frontRunningDetected',

    // Time-based features (5)
    'contractAge', 'lastActivityDays', 'creationBlock', 'deployedDuringBullMarket',
    'launchFairness'
  ];

  // Convert to array
  const featureArray = featureOrder.map(featureName => {
    const value = features[featureName];

    // Handle missing features
    if (value === undefined || value === null) {
      console.warn(`[RugDetector] Missing feature: ${featureName}, using default 0`);
      return 0;
    }

    // Convert boolean to number
    if (typeof value === 'boolean') {
      console.warn(`[RugDetector] WARNING: Boolean detected for ${featureName}: ${value}`);
      return value ? 1 : 0;
    }

    // Return numeric value
    const numValue = Number(value);

    // Debug: Check for NaN or non-numeric
    if (isNaN(numValue)) {
      console.error(`[RugDetector] ERROR: Non-numeric value for ${featureName}: ${value} (type: ${typeof value})`);
      return 0;
    }

    return numValue;
  });

  if (featureArray.length !== 60) {
    throw new Error(`Expected 60 features, got ${featureArray.length}`);
  }

  // Debug: Log feature array types
  console.log(`[RugDetector] Feature array length: ${featureArray.length}`);
  const typeCheck = featureArray.map((v, i) => ({ index: i, type: typeof v, value: v }))
    .filter(item => typeof item.value !== 'number');
  if (typeCheck.length > 0) {
    console.error(`[RugDetector] NON-NUMERIC VALUES DETECTED:`, JSON.stringify(typeCheck));
  }

  return featureArray;
}

/**
 * Extract 18 Uniswap V2-style features for zkML model
 * Simplified feature extraction for Jolt-Atlas compatible model
 * @param {string} contractAddress - Contract address (0x...)
 * @param {string} blockchain - Blockchain name (ethereum, bsc, polygon)
 * @returns {Promise<Array<number>>} - 18 features as array
 */
async function extractZkmlFeatures(contractAddress, blockchain) {
  try {
    // For now, extract comprehensive features and map to zkML subset
    const fullFeatures = await extractFeatures(contractAddress, blockchain);

    // Map 60 features to 18 zkML features
    // Order must match training: mint_count_per_week, burn_count_per_week, mint_ratio, swap_ratio, burn_ratio, etc.
    const zkmlFeatures = [
      fullFeatures.avgDailyTransactions || 0,  // Proxy for mint_count_per_week
      fullFeatures.avgDailyTransactions * 0.5 || 0,  // Proxy for burn_count_per_week
      fullFeatures.liquidityRatio || 0.5,  // mint_ratio proxy
      fullFeatures.transactionVelocity / 100 || 0.3,  // swap_ratio proxy
      0.2,  // burn_ratio - estimated
      3.5,  // mint_mean_period - estimated
      2.0,  // swap_mean_period - estimated
      4.0,  // burn_mean_period - estimated
      fullFeatures.avgDailyTransactions * 10 || 1000,  // swap_in_per_week
      fullFeatures.avgDailyTransactions * 8 || 800,  // swap_out_per_week
      fullFeatures.transactionVelocity / 10 || 15.5,  // swap_rate
      fullFeatures.liquidityPoolSize || 50000,  // lp_avg
      fullFeatures.liquidityPoolSize * 0.1 || 5000,  // lp_std
      fullFeatures.top10HoldersPercent / 100 || 0.1,  // lp_creator_holding_ratio
      fullFeatures.holderCount || 20,  // number_of_holders proxy
      fullFeatures.ownerBalance || 0.05,  // creator_balance_in_lp
      fullFeatures.contractAge / 7 || 30,  // token_age_weeks
      fullFeatures.ownerBalance || 0.15  // token_creator_holding_ratio
    ];

    return zkmlFeatures;
  } catch (error) {
    console.error(`[RugDetector] zkML feature extraction failed:`, error);
    // Return default safe values
    return [100, 50, 0.5, 0.3, 0.2, 3.5, 2.0, 4.0, 1000, 800, 15.5, 50000, 5000, 0.1, 20, 0.05, 30, 0.15];
  }
}

/**
 * Analyze contract using zkML model (18 features, Jolt-Atlas compatible)
 * @param {Array<number>} features - 18 features array
 * @returns {Promise<{riskScore: number, riskCategory: string, confidence: number, probability: number}>}
 */
async function analyzeContractZkml(features) {
  try {
    const { spawn } = require('child_process');
    const fs = require('fs').promises;

    // Load scaler and transform features
    const scalerProc = spawn(PYTHON_PATH, ['-c', `
import pickle
import numpy as np
import json

with open('${ZKML_SCALER_PATH}', 'rb') as f:
    scaler = pickle.load(f)

features = ${JSON.stringify(features)}
scaled = scaler.transform([features])
print(json.dumps(scaled[0].tolist()))
`]);

    let scaledFeatures = await new Promise((resolve, reject) => {
      let stdout = '';
      scalerProc.stdout.on('data', (data) => { stdout += data.toString(); });
      scalerProc.on('close', (code) => {
        if (code !== 0) reject(new Error('Scaler failed'));
        else resolve(JSON.parse(stdout));
      });
      setTimeout(() => { scalerProc.kill(); reject(new Error('Scaler timeout')); }, 5000);
    });

    // Load zkML model
    const session = await onnx.InferenceSession.create(ZKML_MODEL_PATH);

    // Create input tensor
    const inputTensor = new onnx.Tensor('float32', Float32Array.from(scaledFeatures), [1, 18]);

    console.log(`[RugDetector] Running zkML inference (18 features)`);

    // Run inference
    const results = await session.run({ input: inputTensor });
    const output = results.output;
    const probability = output.data[0];  // Sigmoid output: probability of rug pull

    console.log(`[RugDetector] zkML probability: ${probability.toFixed(4)}`);

    // Determine risk category
    let riskCategory, riskScore, confidence;

    if (probability > 0.7) {
      riskCategory = 'high';
      riskScore = 0.7 + (probability - 0.7) * 0.3 / 0.3;
      confidence = probability;
    } else if (probability > 0.4) {
      riskCategory = 'medium';
      riskScore = 0.4 + (probability - 0.4) * 0.3 / 0.3;
      confidence = probability;
    } else {
      riskCategory = 'low';
      riskScore = probability * 0.4;
      confidence = 1 - probability;
    }

    return {
      riskScore: Math.round(riskScore * 100) / 100,
      riskCategory,
      confidence: Math.round(confidence * 100) / 100,
      probability: Math.round(probability * 100) / 100,
      zkml: true
    };

  } catch (error) {
    console.error(`[RugDetector] zkML analysis failed:`, error);
    throw error;
  }
}

module.exports = {
  extractFeatures,
  analyzeContract,
  extractZkmlFeatures,
  analyzeContractZkml,
  ZKML_MODEL_PATH,
  USE_ZKML_MODEL
};
