#!/usr/bin/env python3
"""SwarmChain Epoch Supervisor — keeps the chain running, handles crashes gracefully.

NOT a wrapper script. A proper supervisor that:
1. Runs single_chain.py as a subprocess
2. Monitors for crashes
3. Cleans orphan blocks before restart
4. Logs every restart with reason
5. Never creates duplicate open blocks
6. Runs until epoch target is reached

Usage:
    python3 supervisor.py
"""
import subprocess, sys, time, json, signal, os
import httpx

API_URL = "http://localhost:8080"
API_KEY_FILE = "/tmp/swarmchain_api_key"
STATE_FILE = "single_chain_state.json"
LOG_FILE = "testnet.log"
SESSION = "epoch-2-tier2"
TARGET_BLOCK = 450
CHECK_INTERVAL = 5  # seconds between health checks

running = True

def sig_handler(sig, frame):
    global running
    running = False
    print(f"[supervisor] Received signal {sig}, shutting down...")

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

def get_api_key():
    with open(API_KEY_FILE) as f:
        return f.read().strip()

def clean_orphan_blocks():
    """Close any open blocks before starting a new run."""
    try:
        client = httpx.Client(timeout=30)
        closed = 0
        while True:
            resp = client.get(f"{API_URL}/blocks", params={"status": "open", "limit": 50})
            blocks = resp.json().get("blocks", [])
            if not blocks:
                break
            for b in blocks:
                client.post(f"{API_URL}/blocks/{b['block_id']}/finalize", json={"force": True})
                closed += 1
        if closed > 0:
            print(f"[supervisor] Cleaned {closed} orphan blocks")
    except Exception as e:
        print(f"[supervisor] Orphan cleanup failed: {e}")

def get_last_block():
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_completed_block", 0)
    except:
        return 0

def check_api_health():
    try:
        resp = httpx.get(f"{API_URL}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def run_epoch():
    """Run single_chain.py as subprocess, return exit code."""
    api_key = get_api_key()
    cmd = [
        sys.executable, "-u", "single_chain.py",
        "--api-url", API_URL,
        "--api-key", api_key,
        "--session-id", SESSION,
        "--blocks", str(TARGET_BLOCK),
        "--resume",
    ]
    with open(LOG_FILE, "a") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)
        while running:
            ret = proc.poll()
            if ret is not None:
                return ret
            time.sleep(CHECK_INTERVAL)
        # If we're shutting down, kill the child
        proc.terminate()
        proc.wait(timeout=10)
        return -1

def main():
    print(f"[supervisor] SwarmChain Epoch Supervisor starting")
    print(f"[supervisor] Target: block {TARGET_BLOCK} | Session: {SESSION}")

    restart_count = 0

    while running:
        # Check target
        last = get_last_block()
        if last >= TARGET_BLOCK:
            print(f"[supervisor] Epoch COMPLETE — block {last} >= {TARGET_BLOCK}")
            break

        # Check API health
        if not check_api_health():
            print(f"[supervisor] API not healthy, waiting 10s...")
            time.sleep(10)
            continue

        # Clean orphans before every start
        clean_orphan_blocks()

        # Run
        restart_count += 1
        print(f"[supervisor] Starting run #{restart_count} from block {last}")

        exit_code = run_epoch()

        if not running:
            break

        last_after = get_last_block()
        print(f"[supervisor] Run #{restart_count} exited (code {exit_code}), block {last} → {last_after}")

        if last_after >= TARGET_BLOCK:
            print(f"[supervisor] Epoch COMPLETE — block {last_after}")
            break

        # Brief cooldown before restart
        print(f"[supervisor] Restarting in 5s...")
        time.sleep(5)

    print(f"[supervisor] Supervisor exiting after {restart_count} runs")

if __name__ == "__main__":
    main()
