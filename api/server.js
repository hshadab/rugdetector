// RugDetector API Server
// X402-compliant rug pull detection service

const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');

// Load environment variables
dotenv.config();

// Initialize Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Routes
app.use('/check', require('./routes/check'));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'rugdetector',
    version: '1.0.0',
    uptime: process.uptime()
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    name: 'RugDetector API',
    version: '1.0.0',
    description: 'X402-compliant rug pull detector for autonomous AI agents',
    endpoints: {
      health: '/health',
      check: '/check (POST)',
      discovery: '/.well-known/ai-service.json'
    }
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 RugDetector API running on http://localhost:${PORT}`);
  console.log(`📋 Service discovery: http://localhost:${PORT}/.well-known/ai-service.json`);
  console.log(`💚 Health check: http://localhost:${PORT}/health`);
});
