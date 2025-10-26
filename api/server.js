// RugDetector API Server
// X402-compliant rug pull detection service

const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const rateLimit = require('express-rate-limit');

// Load environment variables
dotenv.config();

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// ===== RATE LIMITING CONFIGURATION =====

// Global rate limit (all endpoints)
const globalLimiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000'), // 1 minute
  max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '60'), // 60 requests per minute
  standardHeaders: true, // Return rate limit info in `RateLimit-*` headers
  legacyHeaders: false, // Disable `X-RateLimit-*` headers
  message: {
    success: false,
    error: 'Too many requests from this IP, please try again later.',
    error_code: 'RATE_LIMIT_EXCEEDED',
    retry_after: '60 seconds'
  },
  // Skip rate limiting for health checks
  skip: (req) => req.path === '/health' || req.path === '/api',
  handler: (req, res) => {
    console.log(`[RateLimit] Blocked request from ${req.ip} to ${req.path}`);
    res.status(429).json({
      success: false,
      error: 'Too many requests from this IP, please try again later.',
      error_code: 'RATE_LIMIT_EXCEEDED',
      retry_after: '60 seconds'
    });
  }
});

// Strict rate limit for payment verification endpoint
const paymentVerificationLimiter = rateLimit({
  windowMs: parseInt(process.env.PAYMENT_RATE_LIMIT_WINDOW_MS || '60000'), // 1 minute
  max: parseInt(process.env.PAYMENT_RATE_LIMIT_MAX || '30'), // 30 payment verifications per minute
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: 'Too many payment verification attempts. Please wait before trying again.',
    error_code: 'PAYMENT_RATE_LIMIT_EXCEEDED',
    retry_after: '60 seconds'
  },
  keyGenerator: (req) => {
    // Rate limit by IP address
    return req.ip;
  },
  handler: (req, res) => {
    console.log(`[PaymentRateLimit] Blocked payment verification from ${req.ip}`);
    res.status(429).json({
      success: false,
      error: 'Too many payment verification attempts. Please wait before trying again.',
      error_code: 'PAYMENT_RATE_LIMIT_EXCEEDED',
      retry_after: '60 seconds'
    });
  }
});

// Middleware
app.use(cors());
app.use(express.json({ limit: '1kb' })); // Limit payload size
app.use(globalLimiter); // Apply global rate limiting

// Serve UI static files
app.use(express.static(path.join(__dirname, '../ui')));

// Serve .well-known directory for X402 service discovery
app.use('/.well-known', express.static(path.join(__dirname, '../public/.well-known')));

// API Routes with rate limiting
app.use('/check', paymentVerificationLimiter, require('./routes/check'));
app.use('/zkml/verify', generalLimiter, require('./routes/zkmlVerify'));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'rugdetector',
    version: '1.0.0',
    commit: 'be5cd3c-onnx-fix',  // ONNX boolean fix deployed
    uptime: process.uptime()
  });
});

// API info endpoint
app.get('/api', (req, res) => {
  res.json({
    name: 'RugDetector API',
    version: '1.0.0',
    description: 'X402-compliant rug pull detector for autonomous AI agents',
    endpoints: {
      ui: '/ (Web UI)',
      health: '/health',
      check: '/check (POST)',
      discovery: '/.well-known/ai-service.json'
    }
  });
});

// Root endpoint - serve UI
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../ui/index.html'));
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 RugDetector running on http://localhost:${PORT}`);
  console.log(`🎨 Web UI: http://localhost:${PORT}`);
  console.log(`📋 Service discovery: http://localhost:${PORT}/.well-known/ai-service.json`);
  console.log(`💚 Health check: http://localhost:${PORT}/health`);
  console.log(`🔌 API endpoint: POST http://localhost:${PORT}/check`);
  console.log('');
  console.log('🛡️  Security Features Enabled:');
  console.log(`   • Global rate limit: ${process.env.RATE_LIMIT_MAX_REQUESTS || '60'} req/min per IP`);
  console.log(`   • Payment rate limit: ${process.env.PAYMENT_RATE_LIMIT_MAX || '30'} verifications/min per IP`);
  console.log(`   • Payment replay prevention: Active (TTL: ${process.env.PAYMENT_CACHE_TTL_SECONDS || '3600'}s)`);
  console.log(`   • Request payload limit: 1kb`);
});
