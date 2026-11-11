# 01: Serve a model with vLLM

Deploy [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B/tree/2fc06364715b967f1860aea9cf38778875588b17) on one NVIDIA GPU and send requests to its OpenAI-compatible API.

## What you will deploy

The [manifest](vllm.yaml) creates a Deployment with one replica and a ClusterIP Service on port `8000`.

| Setting | Value |
| --- | --- |
| vLLM image | `vllm/vllm-openai:v0.33.0`, also pinned by SHA-256 digest |
| GPU allocation | One GPU per Pod |
| Context limit | 2,048 tokens for the prompt and response combined |
| GPU memory budget | 25% of the GPU memory for this vLLM instance |

## 1. Deploy the model

From the browser terminal's `tutorial` folder, enter this lesson:

```bash
cd 01-vllm
```

Print your workload namespace:

```bash
printf '%s\n' "$NAMESPACE"
```

Expect your assigned workload namespace.

Open [vllm.yaml](vllm.yaml) in VS Code before applying it. Review the `vllm serve` arguments, the GPU request, the read-only `/models` mount, and the Service definition.

Apply the server manifest:

```bash
kubectl apply -f vllm.yaml
```

Kubernetes creates `deployment.apps/vllm` and `service/vllm`. Check the Pod status:

```bash
kubectl get pods -o wide
```

Expect one Pod. It becomes ready after vLLM finishes initialization.

## 2. Inspect the logs

Read the startup logs:

```bash
kubectl logs -f deployment/vllm
```

Look for model loading, GPU memory allocation, and API startup. The manifest uses `--enforce-eager` to skip `torch.compile` and CUDA graph capture.

Press `Ctrl+C` to stop following logs.

## 3. Send a chat request

Set the Service URL:

```bash
export VLLM_BASE_URL="http://vllm.${NAMESPACE}.svc:8000"
```

List the served models:

```bash
curl --fail-with-body -sS -m 30 \
  "${VLLM_BASE_URL}/v1/models" | jq '.data[].id'
```

The response should include `"Qwen/Qwen3.5-0.8B"`. Send a prompt using that model name:

```bash
curl --fail-with-body -sS -m 120 \
  "${VLLM_BASE_URL}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3.5-0.8B",
    "messages": [
      {"role": "user", "content": "Explain Kubernetes in one sentence."}
    ],
    "max_tokens": 128,
    "temperature": 0
  }' | jq '{reply: .choices[0].message.content, usage}'
```

Expect a generated reply and token usage. Change the prompt and run the request again. Compare `prompt_tokens` and `completion_tokens`.

### 3.1. Show a streaming reply in the browser

Start the demo in the same terminal:

```bash
export VLLM_MODEL="Qwen/Qwen3.5-0.8B"
export VLLM_MAX_OUTPUT_TOKENS=512
python ../server/demo.py
```

Open <http://127.0.0.1:8080/>.

Enter a prompt and click **Generate**. Expect the reply to stream. Observe time to first token and overall output rate.

The output rate includes the initial wait and the browser and proxy path.

Press `Ctrl+C` in the terminal running the demo server.

## 4. Watch the metrics

Print the monitoring dashboard link:

```bash
echo -e "\n${WORKSHOP_GRAFANA_URL}\n"
```

Open the printed link. Expect the overview with your workload namespace selected. Confirm that it matches `NAMESPACE`.

The engine row shows request queues, KV-cache use, throughput, and latency. The Dynamo frontend row stays empty in this lesson.

### 4.1. Generate load

The `--concurrency` value sets how many requests the traffic client keeps open at the same time. When a request finishes, the client sends the next one.

Run one request at a time:

```bash
export VLLM_MODEL="Qwen/Qwen3.5-0.8B"
python ../server/traffic.py --concurrency 1
```

After one minute, expect one summary line with `completed`, `failed`, and `output_tokens_per_second`. Expect `failed=0`.

Repeat with four concurrent requests:

```bash
python ../server/traffic.py --concurrency 4
```

Expect another summary after one minute. Each request uses the same short prompt and a 256-token output limit.

Compare GPU activity, running requests, KV-cache use, token throughput, and latency between the two runs.

The fixed prompt can reuse cached prefixes, so caching affects the comparison.

> ℹ️ **Note:** GPU data can lag by one minute. In-flight requests are canceled when traffic ends. Cancellations do not count as failures.

## 5. Clean up

From the `01-vllm` folder, delete the resources:

```bash
kubectl delete -f vllm.yaml
```

Kubernetes deletes the Deployment and Service and releases the GPU allocation.

## 6. Next exercise

Continue with [02: Tensor parallelism](../02-tensor-parallel/README.md) to serve a model that does not fit on one GPU.

## Troubleshooting

- If panels are empty, confirm your workload namespace and time range. Run traffic and wait one minute for GPU data. If old Pods appear, narrow the time range to the current run.
- For failed demo or traffic requests, check model readiness, `VLLM_BASE_URL`, and `VLLM_MODEL`.

If startup fails, inspect the Pod:

```bash
kubectl get pods -l app.kubernetes.io/name=vllm
```

Read the Pod status and restart count. Inspect the Pod events:

```bash
kubectl describe pods -l app.kubernetes.io/name=vllm
```

Read the container states and scheduling events. Inspect recent events:

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
```

Look for scheduling, quota, admission, or container failures.

- For `Pending` Pods, check the events for unavailable GPUs, insufficient CPU or memory, or taints that prevent scheduling.
- For `ImagePullBackOff`, check the events for image pull failures and Docker Hub connectivity.
- For `CrashLoopBackOff`, read the previous container logs with `kubectl logs deployment/vllm --previous --tail=200`. Check for missing model files or insufficient GPU memory.
- If no Pod was created, run `kubectl describe deployment vllm` and `kubectl describe replicasets -l app.kubernetes.io/name=vllm`. Look for quota or admission errors.

### Check shared model storage

Check the shared model claim:

```bash
kubectl get pvc workshop-models
```

Expect `Bound`. If the claim or model directory is missing, ask the organizer to check model storage.

If admission reports that shared models must be mounted read-only, keep `readOnly: true` in both the PVC volume source and the container mount. Put writable runtime caches in `/tmp`.

See the [vLLM v0.33.0 Kubernetes deployment documentation](https://docs.vllm.ai/en/v0.33.0/deployment/k8s/) for more deployment options.

## Serving configuration

> ℹ️ **Note:**
> `--language-model-only` serves text without loading the model's vision encoder. `--default-chat-template-kwargs '{"enable_thinking": false}'` disables thinking by default. `--reasoning-parser qwen3` separates any reasoning from the answer returned to the demo.
