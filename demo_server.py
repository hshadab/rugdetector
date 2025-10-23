#!/usr/bin/env python3
"""
Demo Server for RugDetector UI
Simplified server without npm dependencies
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs
import random

class RugDetectorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)

        # Serve UI files
        if parsed_path.path == '/':
            self.send_file('ui/index.html', 'text/html')
        elif parsed_path.path.startswith('/assets/'):
            file_path = 'ui' + parsed_path.path
            if parsed_path.path.endswith('.css'):
                self.send_file(file_path, 'text/css')
            elif parsed_path.path.endswith('.js'):
                self.send_file(file_path, 'application/javascript')
            else:
                self.send_error(404)
        elif parsed_path.path == '/health':
            self.send_json({'status': 'healthy', 'service': 'rugdetector', 'version': '1.0.0'})
        elif parsed_path.path == '/.well-known/ai-service.json':
            self.send_file('public/.well-known/ai-service.json', 'application/json')
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/check':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                result = self.analyze_contract(data)
                self.send_json(result)
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        else:
            self.send_error(404)

    def analyze_contract(self, data):
        """Generate demo analysis results"""
        contract_address = data.get('contract_address', '')
        blockchain = data.get('blockchain', 'ethereum')

        # Use address to generate consistent results
        seed = int(contract_address[-8:], 16) % 10000 if len(contract_address) >= 8 else 0
        random.seed(seed)

        # Determine risk based on address
        is_high_risk = (seed % 5 == 0)
        is_medium_risk = (seed % 3 == 0) and not is_high_risk

        if is_high_risk:
            risk_score = random.uniform(0.65, 0.95)
            risk_category = 'high'
            confidence = random.uniform(0.85, 0.95)
            recommendation = 'High risk detected. Avoid investing. Multiple red flags identified.'
        elif is_medium_risk:
            risk_score = random.uniform(0.35, 0.60)
            risk_category = 'medium'
            confidence = random.uniform(0.75, 0.90)
            recommendation = 'Medium risk detected. Proceed with caution and conduct thorough research.'
        else:
            risk_score = random.uniform(0.05, 0.30)
            risk_category = 'low'
            confidence = random.uniform(0.80, 0.95)
            recommendation = 'Low risk detected. Contract appears relatively safe, but always DYOR.'

        # Generate features
        features = self.generate_features(is_high_risk, is_medium_risk)

        return {
            'success': True,
            'data': {
                'contract_address': contract_address,
                'blockchain': blockchain,
                'riskScore': round(risk_score, 2),
                'riskCategory': risk_category,
                'confidence': round(confidence, 2),
                'features': features,
                'recommendation': recommendation,
                'analysis_timestamp': '2025-10-23T19:00:00Z'
            }
        }

    def generate_features(self, is_high_risk, is_medium_risk):
        """Generate 60 features"""
        features = {}

        # Ownership features
        features['hasOwnershipTransfer'] = 1 if random.random() > 0.3 else 0
        features['hasRenounceOwnership'] = 0 if is_high_risk else 1 if random.random() > 0.5 else 0
        features['ownerBalance'] = random.uniform(0.7, 0.95) if is_high_risk else random.uniform(0.0, 0.3)
        features['ownerTransactionCount'] = random.randint(100, 500) if is_high_risk else random.randint(5, 50)
        features['multipleOwners'] = 1 if random.random() > 0.7 else 0
        features['ownershipChangedRecently'] = 1 if is_high_risk else 0
        features['ownerContractAge'] = random.uniform(1, 30) if is_high_risk else random.uniform(90, 365)
        features['ownerIsContract'] = 1 if random.random() > 0.8 else 0
        features['ownerBlacklisted'] = 1 if is_high_risk else 0
        features['ownerVerified'] = 0 if is_high_risk else 1

        # Liquidity features
        features['hasLiquidityLock'] = 0 if is_high_risk else 1
        features['liquidityPoolSize'] = random.uniform(1000, 10000) if is_high_risk else random.uniform(50000, 500000)
        features['liquidityRatio'] = random.uniform(0.1, 0.3) if is_high_risk else random.uniform(0.5, 0.8)
        features['hasUniswapV2'] = 1 if random.random() > 0.5 else 0
        features['hasPancakeSwap'] = 1 if random.random() > 0.7 else 0
        features['liquidityLockedDays'] = random.uniform(0, 30) if is_high_risk else random.uniform(180, 730)
        features['liquidityProvidedByOwner'] = random.uniform(0.7, 1.0) if is_high_risk else random.uniform(0.0, 0.3)
        features['multiplePoolsExist'] = 1 if random.random() > 0.6 else 0
        features['poolCreatedRecently'] = 1 if is_high_risk else 0
        features['lowLiquidityWarning'] = 1 if is_high_risk else 0
        features['rugpullHistoryOnDEX'] = 0
        features['slippageTooHigh'] = 1 if is_high_risk else 0

        # Holder features
        features['holderCount'] = random.randint(10, 100) if is_high_risk else random.randint(500, 10000)
        features['holderConcentration'] = random.uniform(0.7, 0.95) if is_high_risk else random.uniform(0.1, 0.4)
        features['top10HoldersPercent'] = random.uniform(0.8, 0.98) if is_high_risk else random.uniform(0.2, 0.5)
        features['averageHoldingTime'] = random.uniform(1, 7) if is_high_risk else random.uniform(30, 180)
        features['suspiciousHolderPatterns'] = 1 if is_high_risk else 0
        features['whaleCount'] = random.randint(5, 15) if is_high_risk else random.randint(0, 3)
        features['holderGrowthRate'] = random.uniform(0.5, 2.0) if is_high_risk else random.uniform(0.1, 0.5)
        features['dormantHolders'] = random.uniform(0.6, 0.9) if is_high_risk else random.uniform(0.1, 0.3)
        features['newHoldersSpiking'] = 1 if is_high_risk else 0
        features['sellingPressure'] = random.uniform(0.6, 0.9) if is_high_risk else random.uniform(0.1, 0.4)

        # Code features
        features['hasHiddenMint'] = 1 if is_high_risk else 0
        features['hasPausableTransfers'] = 1 if is_medium_risk else 0
        features['hasBlacklist'] = 1 if random.random() > 0.7 else 0
        features['hasWhitelist'] = 1 if random.random() > 0.8 else 0
        features['hasTimelocks'] = 1 if random.random() > 0.5 else 0
        features['complexityScore'] = random.uniform(0.6, 0.95) if is_high_risk else random.uniform(0.2, 0.5)
        features['hasProxyPattern'] = 1 if random.random() > 0.7 else 0
        features['isUpgradeable'] = 1 if random.random() > 0.6 else 0
        features['hasExternalCalls'] = 1 if random.random() > 0.4 else 0
        features['hasSelfDestruct'] = 1 if is_high_risk else 0
        features['hasDelegateCall'] = 1 if random.random() > 0.7 else 0
        features['hasInlineAssembly'] = 1 if random.random() > 0.6 else 0
        features['verifiedContract'] = 0 if is_high_risk else 1
        features['auditedByFirm'] = 0 if is_high_risk else 1 if random.random() > 0.7 else 0
        features['openSourceCode'] = 0 if is_high_risk else 1

        # Transaction features
        features['avgDailyTransactions'] = random.uniform(500, 2000) if is_high_risk else random.uniform(10, 200)
        features['transactionVelocity'] = random.uniform(0.7, 1.5) if is_high_risk else random.uniform(0.1, 0.5)
        features['uniqueInteractors'] = random.randint(50, 200) if is_high_risk else random.randint(200, 5000)
        features['suspiciousPatterns'] = 1 if is_high_risk else 0
        features['highFailureRate'] = 1 if is_high_risk else 0
        features['gasOptimized'] = 0 if is_high_risk else 1
        features['flashloanInteractions'] = 1 if is_high_risk else 0
        features['frontRunningDetected'] = 1 if is_high_risk else 0

        # Time features
        features['contractAge'] = random.uniform(1, 14) if is_high_risk else random.uniform(90, 730)
        features['lastActivityDays'] = random.uniform(0, 2) if is_high_risk else random.uniform(0, 7)
        features['creationBlock'] = random.randint(18000000, 19000000)
        features['deployedDuringBullMarket'] = 1 if random.random() > 0.5 else 0
        features['launchFairness'] = random.uniform(0.1, 0.4) if is_high_risk else random.uniform(0.6, 0.95)

        return features

    def send_file(self, path, content_type):
        try:
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def send_json(self, data, status=200):
        content = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(content))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server(port=3000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RugDetectorHandler)
    print(f'🚀 RugDetector running on http://localhost:{port}')
    print(f'🎨 Web UI: http://localhost:{port}')
    print(f'🔌 API endpoint: POST http://localhost:{port}/check')
    print(f'💚 Health check: http://localhost:{port}/health')
    print(f'\n✨ Demo Mode: Using simulated analysis (no ML dependencies required)')
    print(f'\nPress Ctrl+C to stop the server')
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    try:
        run_server(port)
    except KeyboardInterrupt:
        print('\n\n👋 Server stopped')
        sys.exit(0)
