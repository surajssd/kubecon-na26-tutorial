# 02: Serve a larger model with tensor parallelism

Deploy [Muse Glimmer 30B](https://huggingface.co/meta-models/Muse-Glimmer-30B/tree/cec94fcfd6512f2cfe708138c32533b346ea4f69) across two NVIDIA L40 GPUs on one node.

## Why two GPUs?

Muse Glimmer's BF16 weights use about 59.6 GB (55.5 GiB), exceeding one L40's 48 GB. Two GPUs provide room for weights, runtime allocations, and KV cache. Available space depends on context length and concurrency.

Tensor parallelism (TP) splits tensor operations across GPUs. Both workers cooperate on each request.

## What you will deploy

Open [vllm.yaml](vllm.yaml) and compare it with [lesson 01's manifest](../01-vllm/vllm.yaml).

| Setting | Value |
| --- | --- |
| vLLM image | `vllm/vllm-openai:v0.33.0`, pinned by SHA-256 digest |
| GPU allocation | Two GPUs in one Pod on one node |
| Tensor parallel size | `2` |
| Context limit | 2,048 tokens for the prompt and response combined |
| Maximum active sequences | `8` |
| GPU memory budget | 90% of each GPU's memory |
| CPU and host memory | Requests 4 CPU cores and 16 GiB; limits 8 CPU cores and 64 GiB |

- `--distributed-executor-backend mp` starts workers within this Pod.
- The `Recreate` strategy releases the old Pod's GPUs before starting its replacement.

## 1. Check your workspace

Complete [lesson 01's cleanup](../01-vllm/README.md#5-clean-up) before continuing. Both lessons reuse the `vllm` Deployment and Service.

Check your GPU quota:

```bash
kubectl get resourcequota gpu-quota
```

Expect GPU quota usage of `0/2`. If usage is not `0/2`, finish the previous lesson's cleanup. Wait for Pod deletion and repeat the check.

> ⚠️ **Caution:**
> The cluster also needs two free GPUs on the same node. Two free GPUs on separate nodes cannot satisfy this Pod's request.

## 2. Deploy and inspect both workers

In the VS Code terminal you used for lesson 01, enter this lesson:

```bash
cd ../02-tensor-parallel
```

Find `--tensor-parallel-size`, `--dtype`, `--gpu-memory-utilization`, and both `nvidia.com/gpu` entries in the manifest [vllm.yaml](vllm.yaml). Apply it:

```bash
kubectl apply -f vllm.yaml
```

Kubernetes creates `deployment.apps/vllm` and `service/vllm`. Check the Pod status:

```bash
kubectl get pods -o wide
```

Expect one Pod. It becomes ready after vLLM finishes initialization.

## 3. Inspect the logs

Read the startup logs:

```bash
kubectl logs -f deployment/vllm
```

Look for TP worker ranks 0 and 1, model loading, and GPU KV-cache capacity.

Press `Ctrl+C` to stop following logs.

Inspect the GPUs:

```bash
kubectl exec deployment/vllm -- nvidia-smi
```

Expect two GPUs with model processes and memory in use, including runtime buffers and KV cache.

## 4. Send a streaming request

Set the Service URL:

```bash
export VLLM_BASE_URL="http://vllm.${NAMESPACE}.svc:8000"
```

List the served model:

```bash
curl --fail-with-body -sS -m 30 \
  "${VLLM_BASE_URL}/v1/models" | jq '.data[].id'
```

Expect `"meta-models/Muse-Glimmer-30B"`.

Start the demo in the same terminal:

```bash
export VLLM_MODEL="meta-models/Muse-Glimmer-30B"
export VLLM_MAX_OUTPUT_TOKENS=512
python ../server/demo.py
```

Open <http://127.0.0.1:8080/>.

Try a short prompt, then a longer prompt with the same output limit. Observe time to first token and overall output rate. Model size and GPU count both changed, so this comparison does not isolate a TP speedup over lesson 01.

Press `Ctrl+C` to stop the demo server.

## 5. Watch the metrics

Print the monitoring dashboard link:

```bash
echo -e "\n${WORKSHOP_GRAFANA_URL}\n"
```

Open the printed link. Expect the overview with your workload namespace selected.

Run four concurrent requests:

```bash
python ../server/traffic.py --concurrency 4
```

Expect one summary after one minute, with `failed=0`. Watch both GPUs under the same Pod and node.

Compare their GPU activity and framebuffer memory.

## 6. Clean up

From the `02-tensor-parallel` folder, run:

```bash
kubectl delete -f vllm.yaml
```

Kubernetes deletes the Deployment and Service and releases both GPUs.

## 7. Next exercise

Continue with [03: Pipeline parallelism](../03-pipeline-parallel/README.md) to split the same model across two nodes with LeaderWorkerSet.

## Troubleshooting

If startup fails, inspect the Pod:

```bash
kubectl describe pods -l app.kubernetes.io/name=vllm
```

Read the container states and scheduling events. If the container restarted, inspect its previous logs:

```bash
kubectl logs deployment/vllm --previous --tail=200
```

Look for model loading or worker initialization errors. Inspect recent events:

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
```

Look for scheduling, quota, admission, or container failures.

- For `Pending`, check GPU quota and whether one node has two free GPUs. If no Pod exists, inspect `kubectl describe replicasets -l app.kubernetes.io/name=vllm` for quota or admission failures.
- For GPU memory errors, keep the GPU request and limit at `2`. Keep TP at `2`, the memory budget at `0.9`, and the context limit at `2048`.
- For `OOMKilled`, inspect host memory usage and the container's memory limit. Host memory and GPU memory are separate limits.
- For NCCL or worker startup errors, retain the shared-memory mount and inspect both worker logs. GPU connectivity affects communication cost.
- If the API or demo shows the wrong model, restart the demo with this lesson's environment exports. Refresh the page.

### Check shared model storage

If model files are missing, check the pinned revision:

```bash
ls /models/meta-models/Muse-Glimmer-30B/cec94fcfd6512f2cfe708138c32533b346ea4f69/config.json
```

Expect the file path. If it is missing, check `/models/catalog.yaml` and ask the organizer to hydrate this revision.

See the [vLLM v0.33.0 parallelism documentation](https://docs.vllm.ai/en/v0.33.0/serving/parallelism_scaling/) for tensor and pipeline parallel deployment options.

## Serving configuration

> ℹ️ **Note:**
> `--default-chat-template-kwargs '{"reasoning_strength": "low"}'` selects low reasoning strength. `--reasoning-parser muse_glimmer` separates reasoning from the answer. The demo shows both separately. Time to first token includes reasoning. The output token count and overall output rate include reasoning tokens.
