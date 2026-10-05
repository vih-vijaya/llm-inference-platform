import json
import time
import urllib.request

URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:0.5b"
PROMPT = "Write a 200-word explanation of GitOps."
RUNS = 5

print(f"Model: {MODEL} | Prompt: {PROMPT}\n")
print("run | tokens | total_sec | tokens_per_sec")

for i in range(1, RUNS + 1):
    body = json.dumps({"model": MODEL, "prompt": PROMPT, "stream": False}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})

    start = time.time()
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    total = time.time() - start

    tokens = data["eval_count"]
    gen_seconds = data["eval_duration"] / 1_000_000_000
    print(f"{i}   | {tokens:6d} | {total:9.2f} | {tokens / gen_seconds:.1f}")