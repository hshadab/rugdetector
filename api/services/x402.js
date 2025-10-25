// X402 Protocol Utilities
// Implements HTTP 402 Payment Required standard
// Spec: https://github.com/coinbase/x402

/**
 * Create X-PAYMENT-RESPONSE header value
 * Returns base64-encoded payment request payload
 */
function createPaymentResponse(options = {}) {
  const {
    amount = '0.1',
    currency = 'USDC',
    network = 'base',
    recipient = process.env.PAYMENT_ADDRESS || '0xYourAddressHere',
    description = 'Smart contract analysis'
  } = options;

  const paymentResponse = {
    schemes: [
      {
        scheme: 'exact',
        network: network,
        currency: currency,
        amount: amount,
        recipient: recipient,
        description: description,
        metadata: {
          service: 'rugdetector',
          version: '1.0.0',
          endpoint: '/check'
        }
      }
    ]
  };

  // Encode to base64
  const jsonString = JSON.stringify(paymentResponse);
  const base64 = Buffer.from(jsonString).toString('base64');

  return base64;
}

/**
 * Parse X-PAYMENT header from request
 * Returns decoded payment payload or null
 */
function parsePaymentHeader(headerValue) {
  if (!headerValue) {
    return null;
  }

  try {
    // Decode from base64
    const jsonString = Buffer.from(headerValue, 'base64').toString('utf-8');
    const payment = JSON.parse(jsonString);

    return payment;
  } catch (error) {
    console.error('[X402] Failed to parse X-PAYMENT header:', error.message);
    return null;
  }
}

/**
 * Validate X402 payment payload structure
 */
function isValidPaymentPayload(payment) {
  if (!payment || typeof payment !== 'object') {
    return false;
  }

  // Check for required fields based on X402 spec
  if (!payment.scheme || !payment.network || !payment.txHash) {
    return false;
  }

  return true;
}

/**
 * Extract transaction hash from X402 payment payload
 */
function extractTransactionHash(payment) {
  if (!payment) {
    return null;
  }

  // X402 payment includes txHash in the payload
  return payment.txHash || null;
}

/**
 * Create X402-compliant 402 error response
 */
function create402Response(res, options = {}) {
  const paymentResponseHeader = createPaymentResponse(options);

  return res
    .status(402)
    .set('X-PAYMENT-RESPONSE', paymentResponseHeader)
    .set('WWW-Authenticate', 'X402')
    .json({
      success: false,
      error: 'Payment required',
      error_code: 'PAYMENT_REQUIRED',
      message: 'This endpoint requires payment. Send 0.1 USDC on Base network.',
      payment_details: {
        amount: options.amount || '0.1',
        currency: options.currency || 'USDC',
        network: options.network || 'base',
        recipient: options.recipient || process.env.PAYMENT_ADDRESS
      },
      hint: 'Include X-PAYMENT header with payment proof, or use demo mode with payment_id starting with "demo_"'
    });
}

module.exports = {
  createPaymentResponse,
  parsePaymentHeader,
  isValidPaymentPayload,
  extractTransactionHash,
  create402Response
};
