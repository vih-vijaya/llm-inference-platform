# LLM Inference Platform

Self-hosted LLM serving on Kubernetes with observability and autoscaling.

This project shows how to run an open-source LLM inside your own infrastructure and operate it like any other production service: containerized, measured, load-tested, autoscaled, and deployed with GitOps.

## Roadmap

| Step | Goal | Status |
|---|---|---|
| 1 | Run a model in Docker and establish a baseline benchmark | Done |
| 2 | FastAPI gateway (API key auth, request logging) | Planned |
| 3 | Deploy to Kubernetes with Helm | Planned |
| 4 | Prometheus metrics and Grafana dashboard | Planned |
| 5 | Load test with k6 (P50/P95/P99) | Planned |
| 6 | Autoscaling with KEDA | Planned |
| 7 | GitOps with Argo CD, final write-up | Planned |

## Step 1: Run a model in Docker and establish a baseline

### Setup
- Machine: Apple Mac (Docker Desktop, CPU-only inference) <!-- add chip and RAM, e.g. M2, 16 GB -->
- Model server: [Ollama](https://ollama.com) running in Docker
- Model: `qwen2.5:0.5b` (0.5 billion parameters, about 400 MB)

### Commands

Start the model server:

```bash
docker run -d --name ollama -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
```

Download the model:

```bash
docker exec -it ollama ollama pull qwen2.5:0.5b
```

Send a first request:

```bash
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:0.5b","prompt":"Explain Kubernetes in one sentence.","stream":false}'
```

Run the benchmark:

```bash
python3 bench.py
```

`bench.py` sends the same prompt 5 times to the Ollama API and prints the tokens generated, total request time, and tokens per second. Tokens/sec is calculated as `eval_count / eval_duration`, using the timing fields Ollama returns in each response.

### Baseline results

**Prompt A:** "Explain Kubernetes in one sentence."

| Run | Tokens | Total (s) | Tokens/sec |
|---|---|---|---|
| 1 | 49 | 0.56 | 122.3 |
| 2 | 46 | 0.31 | 156.4 |
| 3 | 32 | 0.21 | 170.8 |
| 4 | 42 | 0.27 | 170.9 |
| 5 | 53 | 0.47 | 121.4 |

Average: about 148 tokens/sec (range 121 to 171).

**Prompt B:** "Write a 200-word explanation of GitOps."

| Run | Tokens | Total (s) | Tokens/sec |
|---|---|---|---|
| 1 | 120 | 1.20 | 136.4 |
| 2 | 151 | 1.15 | 133.6 |
| 3 | 124 | 0.87 | 144.6 |
| 4 | 145 | 1.10 | 135.2 |
| 5 | 140 | 1.19 | 122.1 |

Average: about 134 tokens/sec (range 122 to 145).

### Cold start (first request after the container started)

The very first `curl` request, made right after the model was downloaded, reported:

| Field | Value |
|---|---|
| `load_duration` | about 0.56 s (time to load the model into memory) |
| `total_duration` | about 0.89 s |
| `eval_count` | 40 tokens |
| `eval_duration` | about 0.26 s (about 152 tokens/sec) |

Loading the model took more time than generating the answer.

### Observations

1. **Longer outputs mean longer total latency.** Prompt B generated about 3x more tokens than Prompt A, and total request time rose from about 0.2 to 0.6 s up to about 0.9 to 1.2 s.
2. **Generation speed stayed in the same band.** Tokens/sec stayed roughly in the 120 to 170 range for both prompts. Total latency depends mostly on how many tokens are generated, so averaging latency alone hides what the server is actually doing.
3. **Cold start is separate from generation speed.** The model load cost (about 0.56 s) appeared in `load_duration` on the first request, not in tokens/sec. A production service should track both, and may keep models warm.
4. **Run-to-run variation is noticeable** (121 to 171 tokens/sec for the same prompt). Short outputs, CPU scheduling, and background load all contribute, so later load tests use many requests and percentiles (P50/P95/P99), not a single number.
5. **CPU-only.** Docker Desktop on a Mac does not give containers access to the Apple GPU, so these numbers are CPU inference. A larger model or a GPU node would change them significantly.

### Key terms
- **Inference:** using a trained model to generate output (as opposed to training it).
- **Token:** the chunk of text a model reads and writes, roughly 3/4 of a word.
- **Tokens/sec:** generation throughput, the LLM equivalent of requests/sec.
- **Cold start:** the extra time to load a model into memory on the first request.

## Repository layout (so far)

```
.
├── README.md
└── bench.py
```