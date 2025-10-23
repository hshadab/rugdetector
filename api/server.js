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

// Serve UI static files
app.use(express.static(path.join(__dirname, '../ui')));

// Serve .well-known directory for X402 service discovery
app.use('/.well-known', express.static(path.join(__dirname, '../public/.well-known')));

// API Routes
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
});
