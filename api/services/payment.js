// X402 Payment Verification Service
// Verifies USDC payments on Base network

const { ethers } = require('ethers');

// USDC contract ABI (minimal - just Transfer event)
const USDC_ABI = [
  'event Transfer(address indexed from, address indexed to, uint256 value)'
];

// Configuration
const BASE_RPC_URL = process.env.BASE_RPC_URL || 'https://mainnet.base.org';
const USDC_CONTRACT_ADDRESS = process.env.USDC_CONTRACT_ADDRESS || '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const EXPECTED_PAYMENT_AMOUNT = parseInt(process.env.PAYMENT_AMOUNT || '100000'); // 0.1 USDC (6 decimals)

// Initialize provider
const provider = new ethers.JsonRpcProvider(BASE_RPC_URL);

/**
 * Verify X402 payment on Base network
 * @param {string} paymentId - Payment ID in format "tx_0x..."
 * @returns {Promise<{verified: boolean, amount: number}>}
 */
async function verifyPayment(paymentId) {
  try {
    // Parse payment ID
    if (!paymentId || typeof paymentId !== 'string') {
      throw new Error('Invalid payment ID format');
    }

    // Extract transaction hash
    let txHash;
    if (paymentId.startsWith('tx_')) {
      txHash = paymentId.substring(3);
    } else if (paymentId.startsWith('0x')) {
      txHash = paymentId;
    } else {
      throw new Error('Payment ID must start with "tx_" or "0x"');
    }

    // Validate transaction hash format
    if (!txHash.match(/^0x[a-fA-F0-9]{64}$/)) {
      throw new Error('Invalid transaction hash format');
    }

    console.log(`[Payment] Verifying transaction: ${txHash}`);

    // Fetch transaction receipt
    const receipt = await provider.getTransactionReceipt(txHash);

    if (!receipt) {
      throw new Error('Transaction not found. Please wait for confirmation.');
    }

    // Check if transaction was successful
    if (receipt.status !== 1) {
      throw new Error('Transaction failed on blockchain');
    }

    console.log(`[Payment] Transaction confirmed in block ${receipt.blockNumber}`);

    // Verify transaction interacted with USDC contract
    if (receipt.to.toLowerCase() !== USDC_CONTRACT_ADDRESS.toLowerCase()) {
      throw new Error('Transaction did not interact with USDC contract');
    }

    // Parse Transfer events from logs
    const usdcContract = new ethers.Contract(USDC_CONTRACT_ADDRESS, USDC_ABI, provider);
    const transferEvents = receipt.logs
      .filter(log => log.address.toLowerCase() === USDC_CONTRACT_ADDRESS.toLowerCase())
      .map(log => {
        try {
          return usdcContract.interface.parseLog(log);
        } catch (e) {
          return null;
        }
      })
      .filter(event => event && event.name === 'Transfer');

    if (transferEvents.length === 0) {
      throw new Error('No USDC transfer found in transaction');
    }

    // Get the first Transfer event (there should typically be only one)
    const transferEvent = transferEvents[0];
    const amount = Number(transferEvent.args.value);

    console.log(`[Payment] Transfer amount: ${amount} USDC units (${amount / 1000000} USDC)`);

    // Verify payment amount
    if (amount < EXPECTED_PAYMENT_AMOUNT) {
      throw new Error(`Insufficient payment amount. Expected: ${EXPECTED_PAYMENT_AMOUNT}, Received: ${amount}`);
    }

    // Payment verified successfully
    console.log(`[Payment] Payment verified successfully`);
    return {
      verified: true,
      amount: amount,
      from: transferEvent.args.from,
      to: transferEvent.args.to,
      txHash: txHash,
      blockNumber: receipt.blockNumber
    };

  } catch (error) {
    console.error(`[Payment] Verification failed:`, error.message);
    throw error;
  }
}

/**
 * Mock payment verification for testing (when no real payment is available)
 * DO NOT USE IN PRODUCTION
 */
async function mockVerifyPayment(paymentId) {
  console.warn('[Payment] WARNING: Using mock payment verification - NOT FOR PRODUCTION');

  // Simulate delay
  await new Promise(resolve => setTimeout(resolve, 500));

  // Always return verified for testing
  return {
    verified: true,
    amount: EXPECTED_PAYMENT_AMOUNT,
    from: '0x0000000000000000000000000000000000000000',
    to: '0x0000000000000000000000000000000000000000',
    txHash: paymentId.replace('tx_', ''),
    blockNumber: 0,
    mock: true
  };
}

module.exports = {
  verifyPayment,
  mockVerifyPayment
};
