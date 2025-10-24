/**
 * Security Features Test Script
 * Tests rate limiting and payment replay prevention
 */

const axios = require('axios');

const API_URL = process.env.API_URL || 'http://localhost:3000';

// Test data
const TEST_CONTRACT = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f';
const TEST_PAYMENT_ID = 'tx_0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testRateLimiting() {
  console.log('\n🧪 Testing Rate Limiting...\n');

  let successCount = 0;
  let rateLimitedCount = 0;

  // Try to make 70 requests (should be rate limited after 60)
  console.log('Sending 70 rapid requests to /health...');

  const requests = [];
  for (let i = 0; i < 70; i++) {
    requests.push(
      axios.get(`${API_URL}/health`)
        .then(() => {
          successCount++;
        })
        .catch((error) => {
          if (error.response && error.response.status === 429) {
            rateLimitedCount++;
          }
        })
    );
  }

  await Promise.all(requests);

  console.log(`✅ Success: ${successCount} requests`);
  console.log(`🛑 Rate limited: ${rateLimitedCount} requests`);

  if (rateLimitedCount > 0) {
    console.log('✅ Rate limiting is working!');
  } else {
    console.log('⚠️  Warning: Expected some requests to be rate limited');
  }
}

async function testPaymentReplayPrevention() {
  console.log('\n🧪 Testing Payment Replay Prevention...\n');

  const samePaymentId = TEST_PAYMENT_ID;

  console.log('Attempt 1: Sending request with payment ID...');

  try {
    const response1 = await axios.post(`${API_URL}/check`, {
      payment_id: samePaymentId,
      contract_address: TEST_CONTRACT,
      blockchain: 'ethereum'
    });

    console.log('  Response:', response1.status);

    // If payment verification succeeds, it should be marked as used
    // If it fails (e.g., no real payment), we still test replay prevention

  } catch (error) {
    if (error.response) {
      console.log('  Response:', error.response.status, error.response.data.error);
    }
  }

  // Wait a moment
  await sleep(1000);

  console.log('\nAttempt 2: Reusing SAME payment ID (should be blocked)...');

  try {
    const response2 = await axios.post(`${API_URL}/check`, {
      payment_id: samePaymentId,
      contract_address: TEST_CONTRACT,
      blockchain: 'ethereum'
    });

    console.log('  Response:', response2.status);
    console.log('❌ Replay attack was NOT prevented! Payment was accepted twice.');

  } catch (error) {
    if (error.response && error.response.status === 402) {
      const errorData = error.response.data;

      if (errorData.error_code === 'PAYMENT_ALREADY_USED') {
        console.log('  Response: 402', errorData.error);
        console.log('✅ Replay attack successfully prevented!');
      } else {
        console.log('  Response: 402', errorData.error);
        console.log('⚠️  Got 402 but not the expected replay prevention error');
      }
    } else if (error.response) {
      console.log('  Response:', error.response.status, error.response.data.error);
      console.log('⚠️  Got an error, but may not be replay prevention');
    } else {
      console.log('  Error:', error.message);
    }
  }
}

async function testPaymentRateLimiting() {
  console.log('\n🧪 Testing Payment Verification Rate Limiting...\n');

  let successCount = 0;
  let rateLimitedCount = 0;

  console.log('Sending 40 rapid payment verification requests...');

  const requests = [];
  for (let i = 0; i < 40; i++) {
    const uniquePaymentId = `tx_0x${i.toString().padStart(64, '0')}`;

    requests.push(
      axios.post(`${API_URL}/check`, {
        payment_id: uniquePaymentId,
        contract_address: TEST_CONTRACT,
        blockchain: 'ethereum'
      })
        .then(() => {
          successCount++;
        })
        .catch((error) => {
          if (error.response && error.response.status === 429) {
            rateLimitedCount++;
          } else if (error.response && error.response.status === 402) {
            // Payment verification failure is expected
            successCount++;
          }
        })
    );
  }

  await Promise.all(requests);

  console.log(`✅ Processed: ${successCount} requests`);
  console.log(`🛑 Rate limited: ${rateLimitedCount} requests`);

  if (rateLimitedCount > 5) {
    console.log('✅ Payment rate limiting is working!');
  } else {
    console.log('⚠️  Warning: Expected more requests to be rate limited');
  }
}

async function testInputValidation() {
  console.log('\n🧪 Testing Input Validation...\n');

  // Test invalid contract address
  console.log('Test 1: Invalid contract address...');
  try {
    await axios.post(`${API_URL}/check`, {
      payment_id: TEST_PAYMENT_ID,
      contract_address: 'invalid',
      blockchain: 'ethereum'
    });
  } catch (error) {
    if (error.response && error.response.status === 422) {
      console.log('  ✅ Invalid address rejected (422)');
    } else {
      console.log('  ⚠️  Got different error:', error.response?.status);
    }
  }

  // Test invalid payment ID format
  console.log('Test 2: Invalid payment ID format...');
  try {
    await axios.post(`${API_URL}/check`, {
      payment_id: 'invalid_payment',
      contract_address: TEST_CONTRACT,
      blockchain: 'ethereum'
    });
  } catch (error) {
    if (error.response && error.response.status === 400) {
      console.log('  ✅ Invalid payment ID rejected (400)');
    } else {
      console.log('  ⚠️  Got different error:', error.response?.status);
    }
  }

  // Test unsupported blockchain
  console.log('Test 3: Unsupported blockchain...');
  try {
    await axios.post(`${API_URL}/check`, {
      payment_id: TEST_PAYMENT_ID,
      contract_address: TEST_CONTRACT,
      blockchain: 'solana'
    });
  } catch (error) {
    if (error.response && error.response.status === 422) {
      console.log('  ✅ Unsupported blockchain rejected (422)');
    } else {
      console.log('  ⚠️  Got different error:', error.response?.status);
    }
  }
}

async function runAllTests() {
  console.log('=================================================');
  console.log('  RugDetector Security Features Test Suite');
  console.log('=================================================');
  console.log(`API URL: ${API_URL}`);

  try {
    // Test health endpoint first
    console.log('\n📡 Checking API health...');
    const health = await axios.get(`${API_URL}/health`);
    console.log('✅ API is healthy:', health.data.status);

    // Run tests
    await testRateLimiting();
    await sleep(2000); // Wait for rate limit to reset

    await testPaymentReplayPrevention();
    await sleep(2000);

    await testPaymentRateLimiting();
    await sleep(2000);

    await testInputValidation();

    console.log('\n=================================================');
    console.log('  All tests completed!');
    console.log('=================================================\n');

  } catch (error) {
    console.error('\n❌ Error during tests:', error.message);
    if (error.code === 'ECONNREFUSED') {
      console.error('⚠️  Make sure the API server is running on', API_URL);
    }
  }
}

// Run tests
runAllTests();
