#!/bin/bash
#
# Alchemy API Setup Script for RugDetector
# This script helps you configure your Alchemy API key
#

set -e

echo "========================================================================"
echo "Alchemy API Setup for RugDetector"
echo "========================================================================"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
fi

# Check if already configured
if grep -q "YOUR_ALCHEMY_API_KEY" .env; then
    echo "ℹ️  Your .env file has placeholder Alchemy API keys"
    echo ""
    echo "To configure Alchemy:"
    echo ""
    echo "1. Get your free API key:"
    echo "   → Go to https://www.alchemy.com/"
    echo "   → Sign up (free, no credit card required)"
    echo "   → Create App: 'RugDetector'"
    echo "   → Network: Ethereum Mainnet"
    echo "   → Copy your API key"
    echo ""
    echo "2. Update your .env file:"
    echo "   → Open: nano .env"
    echo "   → Replace: YOUR_ALCHEMY_API_KEY"
    echo "   → With: Your actual API key"
    echo ""
    echo "3. Or use this command:"
    echo ""
    read -p "Do you have an Alchemy API key? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        read -p "Enter your Alchemy API key: " ALCHEMY_KEY

        if [ -z "$ALCHEMY_KEY" ]; then
            echo "❌ No key entered. Exiting."
            exit 1
        fi

        echo ""
        echo "Updating .env file..."

        # Update .env file with the API key
        sed -i.backup "s|YOUR_ALCHEMY_API_KEY|$ALCHEMY_KEY|g" .env

        echo "✓ Updated .env file"
        echo "✓ Backup saved to .env.backup"
        echo ""
        echo "========================================================================"
        echo "Configuration Complete!"
        echo "========================================================================"
        echo ""
        echo "Your Alchemy endpoints are now configured:"
        echo "  • Base: https://base-mainnet.g.alchemy.com/v2/$ALCHEMY_KEY"
        echo "  • Solana: https://solana-mainnet.g.alchemy.com/v2/$ALCHEMY_KEY"
        echo ""
        echo "Next steps:"
        echo "  1. Restart your server:"
        echo "     pkill -f 'node.*server.js' && PORT=3000 node api/server.js"
        echo ""
        echo "  2. Test feature extraction:"
        echo "     curl -X POST http://localhost:3000/check \\"
        echo "       -H 'Content-Type: application/json' \\"
        echo "       -d '{\"contract_address\":\"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913\",\"blockchain\":\"base\",\"payment_id\":\"demo_test\"}'"
        echo ""
    else
        echo ""
        echo "No problem! Get your Alchemy API key first:"
        echo ""
        echo "  1. Visit: https://www.alchemy.com/"
        echo "  2. Sign up (free)"
        echo "  3. Create an app"
        echo "  4. Copy your API key"
        echo "  5. Run this script again"
        echo ""
    fi
else
    echo "✓ Alchemy API appears to be already configured"
    echo ""
    echo "Current Base RPC URL:"
    grep "BASE_RPC_URL" .env | head -1
    echo ""
    echo "If you need to reconfigure, edit .env manually:"
    echo "  nano .env"
    echo ""
fi

echo "========================================================================"
echo "Alchemy Free Tier Benefits:"
echo "========================================================================"
echo "  • 300 million compute units/month"
echo "  • ~300 requests/second sustained"
echo "  • 99.9% uptime SLA"
echo "  • Full archive data access"
echo "  • Enhanced APIs (NFTs, Transfers, WebSockets)"
echo ""
echo "For RugDetector: Enough for ~15 million contract analyses/month"
echo ""
echo "Documentation: See ALCHEMY_SETUP.md for detailed guide"
echo "========================================================================"
