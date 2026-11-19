import argparse
import csv
import subprocess
import time

OPENSSL_BIN = "/opt/openssl-3.5/bin/openssl"
ENV_PREFIX = ["ip", "netns", "exec", "ns_client", "env", "LD_LIBRARY_PATH=/opt/openssl-3.5/lib64"]

def run_single_client(mode: str) -> tuple[bool, float]:
    groups = "X25519" if mode == "M0" else "X25519MLKEM768"
    cmd = ENV_PREFIX + [
        OPENSSL_BIN, "s_client",
        "-connect", "10.0.1.2:4433",
        "-groups", groups,
        "-tls1_3", "-ign_eof"
    ]
    req = b"GET / HTTP/1.1\r\nHost: pqc-proxy.local\r\nConnection: close\r\n\r\n"
    
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, input=req, capture_output=True, timeout=15)
    t1 = time.perf_counter()
    
    success = (proc.returncode == 0) and (b"OK_PQC_RELAY_VERIFIED" in proc.stdout)
    return success, (t1 - t0) * 1000.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["M0", "M1"])
    parser.add_argument("--profile", required=True, choices=["P0", "P3"])
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--out", default="results/client_bench.csv")
    args = parser.parse_args()

    # Start tcpdump on Leg A (veth_p_a) for wire-level PCAP verification
    pcap_path = f"results/capture_{args.mode}_{args.profile}.pcap"
    tcpdump = subprocess.Popen([
        "ip", "netns", "exec", "ns_proxy",
        "tcpdump", "-i", "veth_p_a", "-w", pcap_path, "tcp port 4433"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)

    successes = 0
    with open(args.out, "a", newline="") as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(["run_id", "mode", "profile", "success", "client_total_ms"])

        for i in range(1, args.runs + 1):
            try:
                ok, elapsed_ms = run_single_client(args.mode)
            except subprocess.TimeoutExpired:
                ok, elapsed_ms = False, 15000.0
            if ok:
                successes += 1
            writer.writerow([i, args.mode, args.profile, int(ok), f"{elapsed_ms:.3f}"])

    time.sleep(0.5)
    tcpdump.terminate()
    print(f"[{args.mode} | {args.profile}] Completed {args.runs} runs | Success: {successes}/{args.runs} ({successes/args.runs*100:.1f}%)")

if __name__ == "__main__":
    main()