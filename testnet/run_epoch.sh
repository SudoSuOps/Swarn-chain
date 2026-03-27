#!/bin/bash
cd /data2/swarmchain/testnet
echo "$(date) === EPOCH 2 STABILITY TEST === 5 bees → Zima controller"
while true; do
    python3 -c "
import httpx
client = httpx.Client(timeout=30)
while True:
    resp = client.get('http://192.168.0.70:8080/blocks', params={'status':'open','limit':50})
    blocks = resp.json().get('blocks',[])
    if not blocks: break
    for b in blocks:
        client.post('http://192.168.0.70:8080/blocks/' + b['block_id'] + '/finalize', json={'force':True})
" 2>/dev/null
    timeout 120 python3 -u single_chain.py \
        --api-url http://192.168.0.70:8080 \
        --api-key "" \
        --session-id epoch-2-stability \
        --blocks 250 \
        --resume >> testnet.log 2>&1
    LAST=$(python3 -c "import json; print(json.load(open('single_chain_state.json'))['last_completed_block'])" 2>/dev/null)
    [ "$LAST" -ge 250 ] 2>/dev/null && break
    sleep 3
done
echo "$(date) === EPOCH 2 COMPLETE ==="
