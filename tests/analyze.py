import pandas as pd
import numpy as np

proxy_df = pd.read_csv("results/proxy_metrics.csv")
client_df = pd.read_csv("results/client_bench.csv")

print("=== PROXY-SIDE HANDSHAKE & SEGMENT METRICS ===")
summary = proxy_df[proxy_df["outcome"] == "SUCCESS"].groupby(["profile", "mode"]).agg(
    count=("hs_time_ms", "count"),
    median_hs_ms=("hs_time_ms", "median"),
    p95_hs_ms=("hs_time_ms", lambda x: np.percentile(x, 95)),
    mean_segs_in=("segs_in", "mean"),
    mean_segs_out=("segs_out", "mean"),
    total_retrans=("retrans_delta", "sum")
)
print(summary.to_string())

print("\n=== CLIENT-SIDE END-TO-END COMPLETION (200 RUNS) ===")
c_summary = client_df.groupby(["profile", "mode"]).agg(
    success_rate=("success", lambda x: f"{x.mean()*100:.1f}%"),
    median_ms=("client_total_ms", "median"),
    p95_ms=("client_total_ms", lambda x: np.percentile(x, 95))
)
print(c_summary.to_string())