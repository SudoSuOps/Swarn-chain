#!/bin/bash
# Auto-restart wrapper for single-chain testnet
cd /data2/swarmchain/testnet
API_KEY=$(cat /tmp/swarmchain_api_key)

while true; do
    echo "$(date) Starting single-chain testnet (--resume)..."
    python3 -u single_chain.py \
        --api-url http://165.227.109.67/api \
        --api-key "$API_KEY" \
        --session-id testnet-001 \
        --blocks 1000 \
        --resume >> testnet.log 2>&1
    
    EXIT_CODE=$?
    echo "$(date) Process exited with code $EXIT_CODE" >> testnet.log
    
    # Check if we're done (all 1000 blocks)
    LAST=$(python3 -c "import json; d=json.load(open('single_chain_state.json')); print(d['last_completed_block'])" 2>/dev/null)
    if [ "$LAST" = "1000" ]; then
        echo "$(date) TESTNET COMPLETE — 1000 blocks sealed" >> testnet.log
        break
    fi
    
    echo "$(date) Restarting in 5s..." >> testnet.log
    sleep 5
done
