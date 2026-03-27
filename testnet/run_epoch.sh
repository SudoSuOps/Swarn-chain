#!/bin/bash
cd /data2/swarmchain/testnet
API_KEY=$(cat /tmp/swarmchain_api_key)

echo "$(date) === EPOCH 3 START === blocks 300-600"
while true; do
    python3 -u single_chain.py \
        --api-url http://localhost:8080 \
        --api-key "$API_KEY" \
        --session-id epoch-3 \
        --blocks 600 \
        --resume >> testnet.log 2>&1
    
    LAST=$(python3 -c "import json; d=json.load(open('single_chain_state.json')); print(d['last_completed_block'])" 2>/dev/null)
    if [ "$LAST" -ge 600 ] 2>/dev/null; then
        echo "$(date) === EPOCH 3 COMPLETE === block $LAST"
        break
    fi
    echo "$(date) Restarting in 3s..." >> testnet.log
    sleep 3
done
echo "$(date) === COOLDOWN — extract data, analyze, adjust ==="
