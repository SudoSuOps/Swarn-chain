#!/bin/bash
# Deploy SwarmChain frontend to IPFS for swarmchain.eth.limo
#
# Prerequisites:
#   npm install -g @web3-storage/w3cli   (or use ipfs CLI)
#   OR: manually upload dist/ to pinata.cloud / web3.storage
#
# Usage:
#   ./deploy-ipfs.sh [api-url]
#
# The API URL is baked into the build. For production:
#   ./deploy-ipfs.sh https://api.swarmchain.eth.limo
#
# After upload, set ENS contenthash:
#   1. Go to app.ens.domains → swarmchain.eth → Records
#   2. Set Content Hash to: ipfs://<CID>
#   3. Save + confirm transaction
#   4. Wait ~5 min for propagation
#   5. Visit: https://swarmchain.eth.limo

set -euo pipefail

API_URL="${1:-https://api.swarmchain.eth.limo}"

echo "============================================"
echo "  SwarmChain Frontend → IPFS Deploy"
echo "============================================"
echo "  API URL: ${API_URL}"
echo ""

# Build with production API URL
echo "Building frontend..."
VITE_API_URL="${API_URL}" npm run build

echo ""
echo "Build complete: dist/"
echo ""
ls -lah dist/
echo ""

# Check for IPFS CLI tools
if command -v w3 &> /dev/null; then
    echo "Uploading to web3.storage via w3 CLI..."
    CID=$(w3 up dist/ --no-wrap 2>&1 | grep -oP 'bafy\w+' | head -1)
    echo ""
    echo "============================================"
    echo "  UPLOADED TO IPFS"
    echo "============================================"
    echo "  CID: ${CID}"
    echo "  Gateway: https://${CID}.ipfs.w3s.link"
    echo ""
    echo "  Next: set ENS contenthash to ipfs://${CID}"
    echo "  Then: https://swarmchain.eth.limo"
    echo "============================================"
elif command -v ipfs &> /dev/null; then
    echo "Uploading to IPFS via local node..."
    CID=$(ipfs add -r -Q dist/)
    echo ""
    echo "============================================"
    echo "  PINNED TO IPFS"
    echo "============================================"
    echo "  CID: ${CID}"
    echo "  Next: set ENS contenthash to ipfs://${CID}"
    echo "============================================"
else
    echo "============================================"
    echo "  BUILD READY — MANUAL UPLOAD NEEDED"
    echo "============================================"
    echo ""
    echo "  No IPFS CLI found. Upload dist/ manually:"
    echo ""
    echo "  Option 1: https://app.pinata.cloud (drag & drop dist/)"
    echo "  Option 2: https://web3.storage (upload dist/)"
    echo "  Option 3: Install w3 CLI: npm i -g @web3-storage/w3cli"
    echo ""
    echo "  After upload, set ENS contenthash:"
    echo "    1. app.ens.domains → swarmchain.eth → Records"
    echo "    2. Content Hash → ipfs://<CID>"
    echo "    3. Save + confirm tx"
    echo "    4. Visit: https://swarmchain.eth.limo"
    echo "============================================"
fi
