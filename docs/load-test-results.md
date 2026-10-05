# Load test results: baseline (1 Ollama replica)

**Setup:** kind cluster on <chip, RAM>, Docker Desktop memory <X> GB,
1 Ollama replica (qwen2.5:0.5b, CPU only), 1 gateway replica.
**Tool:** k6, ramping 1 → 3 → 6 → 10 virtual users over 4m30s.
**Prompts:** 5 short prompts chosen at random.

## Overall
| Metric | Value |
|---|---|
| Total requests | 239 |
| Average throughput | 0.89 req/s |
| Error rate | 0% (0 of 239) |
| Latency min / median | 0.20 s / 2.98 s |
| Latency P90 / P95 / P99 | 11.01 s / 12.86 s / 15.95 s |
| Latency max | 17.24 s |
| Threshold P95 < 5 s | Failed (12.86 s) |

## By concurrency (read from Grafana)
| Virtual users | Approx. req/s | P95 latency | Notes |
|---|---|---|---|
| 1 | | | |
| 3 | | | |
| 6 | | | |
| 10 | | | |

## Findings
- No errors or timeouts, but latency rose steeply with concurrency: the median
  was 15x the fastest request and P99 reached about 16 s.
- Throughput did not scale with users: <describe what your Grafana panel showed>.
- Requests queue behind each other on a single CPU-bound model server.
- Bottleneck: <CPU usage you saw in docker stats, if you checked>.

## Limitations
- Requests went through `kubectl port-forward`, not a production ingress.
- CPU-only inference on a laptop; GPU nodes would change absolute numbers.
- One short run; results vary between runs.