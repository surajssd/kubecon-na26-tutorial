---
class: debrief-slide
---

<p class="kicker">Debrief · lesson 1</p>

# Four at Once Finished More Work

<p class="debrief-source"><span class="badge live">Measured on this cluster</span></p>

<ConcurrencyLanes class="debrief-lanes" :runs="[{ concurrency: 1, completed: 15 }, { concurrency: 4, completed: 52 }]" />

This small model uses little GPU memory. The next model's weights exceed one GPU's memory.

<style>
.debrief-slide { display: flex; flex-direction: column; }
.debrief-slide .debrief-source { margin: 0; }
.debrief-lanes { margin: 22px 0 8px; }
</style>

<!--
Each one-minute `traffic.py` run used Qwen3.5-0.8B, one fixed prompt, and a 256-token output limit. Cached prefixes can affect the result. These are workshop observations.

The limit of 8 comes from `--max-num-seqs 8` in the lesson 1 manifest. Your values can differ because the shared cluster, cached prefixes, and the one-minute window all affect the count.

Each decode step can serve several requests. It can generate a token for each active request. Batching shares the work of reading the weights across those requests.

At concurrency 1, 15 requests finished in one minute. At concurrency 4, 52 requests finished in one minute. With four requests open, one request finished about every 1.2 seconds on average. `traffic.py` reports counts rather than individual request times. The dashboard's latency panel provides measured latency.

Each box represents one finished request. The two runs used separate one-minute windows. Within each run, the rows operated at the same time. Box widths do not represent request durations.
-->

---
layout: lesson-transition
problem: Muse Glimmer 30B in BF16 Does Not Fit on One L40
next: 2
---

<v-clicks at="1">

1. Stop the demo with <kbd>Ctrl+C</kbd> if it still runs.
2. Delete lesson 1:

</v-clicks>

<v-click at="2">

```bash
kubectl delete -f vllm.yaml
```

</v-click>

<v-clicks at="3">

3. Check your GPU quota. Expect `0/2` in use:

</v-clicks>

<v-click at="3">

```bash
kubectl get resourcequota gpu-quota
```

</v-click>

<!--
The scale test measured about 217 seconds to readiness for lesson 2.

GPU quota remains in use while the lesson 1 Pod terminates. Lesson 2 needs both GPUs, so it cannot start until that usage returns to 0/2.
-->

---
layout: chapter
lesson: 2
---

# Batching, Memory, and Tensor Parallelism

While Muse Glimmer loads: why concurrency 4 did more work, what limits it, and how one model spans two GPUs.

<!--
Batching determines which requests share a step. KV cache capacity limits how many requests can stay active. Tensor parallelism lets a model use more than one GPU when it does not fit on one.
-->

---
class: sim-slide
---

<ContinuousBatching />

<!--
Continuous batching can give a freed sequence slot to a waiting request at the next step. Static batching holds that slot until the rest of the batch finishes.

With uneven lengths, r1 finishes after step 2. Static batching holds its slot, while continuous batching gives it to r3 at step 3. Both policies emit 9 tokens, but static batching takes 7 steps and continuous batching takes 5. They leave 5 and 1 idle slot-steps respectively.

With equal lengths, both policies take 6 steps. Refilling helps when requests finish at different times.

Occupancy here measures sequence slots only. This example models decode only and supplies neither TTFT nor GPU utilization.
-->

---
layout: center
class: slides-link
---

# Try the Simulations

<img class="slides-qr" src="../assets/continuous-batching-qr.svg" alt="QR code for https://suraj.io/kubecon-na26/#/25" width="300" height="300">

<a class="slides-url" href="https://suraj.io/kubecon-na26/#/25" target="_blank">suraj.io/kubecon-na26/#/25</a>

<style>
.slides-link { text-align: center; }
.slides-link .slides-qr { display: block; width: 300px; height: 300px; margin: 20px auto; }
.slides-link .slides-url { font-size: 1.6rem; font-weight: 700; color: var(--ink); }
</style>

---

<p class="kicker">Operational guidance</p>

# Queues and Latency Reveal Unmet Demand

<div class="cols">
<div>

<v-clicks at="1">

- **GPU utilization** reports the share of time that any kernel ran. One small request can keep it high.
- **Waiting requests** show demand that the server cannot serve yet.
- **Time to first token** shows how long users wait for output.
- Check both alongside running requests and KV-cache use.

</v-clicks>

</div>
<div class="cols-stack">
  <div v-click="5" class="card good"><h2>Capacity signals</h2><p>Queue growth, latency, and KV-cache use</p></div>
  <div v-click="6" class="card bad"><h2>GPU utilization alone is insufficient</h2><p>Busy time does not show how much more work fits.</p></div>
</div>
</div>

<style>
.cols-stack { display: flex; flex-direction: column; gap: 12px; }
.card.good { border-color: var(--live); }
.card.bad { border-color: var(--accent); }
</style>

<!--
In lesson 1's Grafana panels, concurrency 4 raised the running count while waiting stayed near zero. That comparison demonstrates batching. Sustained queue growth and latency above the service target are reasons to investigate capacity.

vLLM exposes `vllm:num_requests_running` and `vllm:num_requests_waiting`. Model loading takes time, so a scaling policy must allow for startup delays.
-->

---
clicks: 3
class: kv-cache-slide
---

<p class="kicker">Claim 1 · memory</p>

# What the KV Cache Stores

<p v-click="1">The KV cache stores keys and values for reuse during decode.</p>

<div class="kv-fit">
<div v-click="2">
<StackedBar title="1 GiB of KV cache: 4 requests with 2,048 cached tokens each" :segments="[{ label: 'Request 1', value: 1, tone: 'kv' }, { label: 'Request 2', value: 1, tone: 'kv' }, { label: 'Request 3', value: 1, tone: 'kv' }, { label: 'Request 4', value: 1, tone: 'kv' }]" />
</div>
<div v-click="3">
<StackedBar title="1 GiB of KV cache: 2 requests with 4,096 cached tokens each" :segments="[{ label: 'Request 1', value: 1, tone: 'kv' }, { label: 'Request 2', value: 1, tone: 'kv' }]" />

> Longer contexts leave room for fewer requests.

</div>
</div>

<p class="muted small kv-assumption">Illustrative full-attention BF16 layout: 128 KiB per cached token.</p>

<style>
.kv-cache-slide { display: flex; flex-direction: column; }
.kv-fit { display: flex; flex-direction: column; gap: 24px; margin-top: 12px; }
.kv-cache-slide .kv-assumption { margin-top: auto; margin-bottom: 0; }
/* Keep the unit GiB readable: StackedBar captions are uppercase by default. */
.kv-fit :deep(figcaption) { font-size: 1rem; text-transform: none; letter-spacing: 0; }
</style>

<!--
Every layer computes a key and a value vector for each token it processes. The server keeps them so decode can reuse the processed prompt. Each decode step adds one processed token to the cache.

KV bytes per cached token equal `2 × layers × KV heads × head dimension × bytes per element`.

For this illustrative BF16 layout, `2 × 32 × 8 × 128 × 2 = 128 KiB` per cached token. A request with 2,048 cached tokens uses 256 MiB.

The factor 2 is one key plus one value. Models with grouped-query attention have fewer KV heads than query heads, which shrinks the cache.

This formula covers one full-attention layout only. Models with sliding-window or hybrid attention use other formulas; lesson 4's Gemma is one of them.

The bars use the same illustrative layout: 128 KiB per token. The same 1 GiB holds 4 requests of 2,048 tokens, or only 2 requests of 4,096 tokens. A longer context length means fewer requests at once. This is the same math as the startup log line "Maximum concurrency for 2,048 tokens per request".

More requests in the cache means more requests in each decode step. The step reads the weights once either way, so the same requests finish in fewer steps. When the cache is full, vLLM preempts a request and later recomputes its cache. A bigger cache avoids that extra work.
-->

---
class: sim-slide
---

<KvCache />

<!--
A request needs KV blocks for its prompt and generated output. Memory can therefore limit concurrency before the sequence limit does.

With 1-token blocks, `r1` to `r3` reserve 45 of 48 blocks. `r4` needs 11, so it waits even though only 3 of 4 sequence slots are busy. When `r1` finishes at step 6, its blocks return to the pool and r4 can start at the next step.

With 4-token blocks, a request can leave unused space inside its allocated blocks. Freed blocks can still be reused by other requests.

This teaching policy reserves each request's peak need up front. vLLM admits more aggressively and preempts a request when blocks run out. The simulation illustrates a memory limit and simplifies vLLM's scheduling policy.
-->

---
layout: center
class: slides-link
---

# Try the Simulations

<img class="slides-qr" src="../assets/kv-cache-qr.svg" alt="QR code for https://suraj.io/kubecon-na26/#/29" width="300" height="300">

<a class="slides-url" href="https://suraj.io/kubecon-na26/#/29" target="_blank">suraj.io/kubecon-na26/#/29</a>

<style>
.slides-link { text-align: center; }
.slides-link .slides-qr { display: block; width: 300px; height: 300px; margin: 20px auto; }
.slides-link .slides-url { font-size: 1.6rem; font-weight: 700; color: var(--ink); }
</style>

---

<p class="kicker">Hardware · lesson 2</p>

# Why Muse Glimmer Needs Two GPUs

<div class="memory">
<StackedBar v-click="1" title="Muse Glimmer 30B, BF16 checkpoint" :segments="[{ label: 'Weights: about 59.6 GB (55.5 GiB)', value: 59.6, tone: 'weights' }]" :scale="59.6 / 96" />
<StackedBar v-click="2" title="One NVIDIA L40" :segments="[{ label: '48 GB', value: 48, tone: 'free' }, { label: '11.6 GB short', value: 11.6, tone: 'over' }]" :scale="59.6 / 96" />
<StackedBar v-click="3" title="Two L40 GPUs with tensor parallelism" :segments="[{ label: 'GPU 0: half the weights + KV cache', value: 48, tone: 'kv' }, { label: 'GPU 1: half the weights + KV cache', value: 48, tone: 'kv' }]" />
</div>

<v-clicks at="4">

- A dense model needs all of its weights for every token. They must fit in GPU memory with room left for the KV cache.
- The vLLM logs show **26.11 GiB** of model memory on each GPU with TP 2.

</v-clicks>

<style>
.memory { display: flex; flex-direction: column; gap: 12px; margin: 12px 0; }
</style>

<!--
`Model loading took` in `kubectl logs deployment/vllm` reports the model's memory allocation. Our measured value is 26.11 GiB per TP worker. vLLM prints this message only from the first local rank, so one log line does not mean only one GPU loaded weights.

vLLM partitions the weight tensors according to `--tensor-parallel-size 2`. Each TP worker loads its assigned part onto its GPU. Kubernetes allocates both GPUs to the Pod; vLLM handles the model split.

`kubectl exec deployment/vllm -- nvidia-smi` reports total memory use on both GPUs. Each total also includes runtime buffers and KV cache, so it exceeds the model allocation in the startup log.

48 GB is the L40's memory. 59.6 GB of weights does not fit, even before runtime buffers and KV cache. Lesson 2 gives vLLM 90% of each of two GPUs.
-->

---
clicks: 9
---

<p class="kicker">Tensor parallelism · lesson 2</p>

# Split Every Layer Across Two GPUs

<div class="cols tp-slide">
<TensorParallel :step="$clicks" />
<div>

<v-clicks at="1">

- vLLM: `--tensor-parallel-size 2`
- Kubernetes: **one Pod** that requests `nvidia.com/gpu: 2`
- The GPUs exchange data at every layer, so a fast link matters.
- This lesson's **single Pod** places both GPUs on **one node**.

</v-clicks>

<v-click at="4">

> Two free GPUs on different nodes cannot run this Pod.

</v-click>

</div>
</div>

<style>
.tp-slide { grid-template-columns: 1.25fr 1fr; margin-top: 10px; }
</style>

<!--
Both GPUs work on the same token's intermediate state. Each computes part of a layer, then exchanges partial results with the other GPU. After the final layer, the output head and sampling produce the next token.

The four-layer example and single exchange per layer simplify the real model and its collectives. Animation duration does not represent compute or communication time.

This animation shows one decode step. Both GPUs compute part of each layer and exchange partial results before continuing.

Source: https://developer.nvidia.com/blog/boosting-llama-3-1-405b-throughput-by-another-1-5x-on-nvidia-h200-tensor-core-gpus-and-nvlink-switch/

Each GPU stores half of each weight matrix. After each layer, the GPUs combine their partial results (an all-reduce), so communication happens many times per token. TP can span nodes, but a slower link adds communication overhead. This lesson places both GPUs in one Pod.

The TP workers have ranks 0 and 1. Their startup logs describe model loading and GPU KV cache capacity.
-->

---

# Lesson 1 to 2: The Config Diff

<div class="config-diff-legend"><span class="config-removed">− Lesson 1</span><span class="config-added">+ Lesson 2</span></div>

<h2 v-click="1">vLLM arguments</h2>

<pre v-click="1" class="config-diff"><code><span class="config-removed">- /models/Qwen/Qwen3.5-0.8B/…</span>
<span class="config-added">+ /models/meta-models/Muse-Glimmer-30B/…</span>
<span class="config-added">+ --tensor-parallel-size 2</span>
<span class="config-added">+ --distributed-executor-backend mp</span>
<span class="config-removed">- --gpu-memory-utilization 0.25</span>
<span class="config-added">+ --gpu-memory-utilization 0.9</span></code></pre>

<h2 v-click="2">Kubernetes GPU resources</h2>

<pre v-click="2" class="config-diff"><code><span class="config-removed">- nvidia.com/gpu: 1</span>
<span class="config-added">+ nvidia.com/gpu: 2</span></code></pre>

<p v-click="2" class="small">The GPU count changes in both <code>requests</code> and <code>limits</code>. Both GPUs belong to one Pod.</p>
<p v-click="2" class="muted small">Selected settings only. Model revision hashes are abbreviated.</p>

<style>
.config-diff-legend { display: flex; gap: 28px; margin: 12px 0 16px; font-size: 0.95rem; font-weight: 700; }
.config-removed { color: var(--req-2); }
.config-added { color: var(--req-4); }
.config-diff { margin: 8px 0 14px; padding: 8px 0; border: 1px solid var(--line); border-radius: 8px; background: var(--slidev-code-background); }
.config-diff code { display: block; font-family: var(--mono); font-size: 0.95rem; line-height: 1.5; }
.config-diff span { display: inline-block; width: 100%; padding: 0 14px; }
.config-diff .config-removed { background: color-mix(in srgb, var(--req-2) 10%, transparent); }
.config-diff .config-added { background: color-mix(in srgb, var(--req-4) 10%, transparent); }
</style>

<!--
Lesson 2 changes the model and GPU configuration from lesson 1. Both manifests pin the model revision.

Tensor parallelism splits the larger model across two GPUs, and `mp` runs the workers as local processes. The memory budget rises from 25% to 90% of each GPU's memory. Kubernetes allocates both GPUs to the same Pod.

Model precision stays BF16. Lesson 1 uses the default `--dtype auto`, which selects BF16 from Qwen's model configuration. Lesson 2 sets `--dtype bfloat16` explicitly. Sources: [vLLM dtype selection](https://docs.vllm.ai/en/v0.33.0/configuration/engine_args/#dtype), [pinned Qwen configuration](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/2fc06364715b967f1860aea9cf38778875588b17/config.json).

The served model name and model-specific reasoning settings also change. CPU and host-memory resources and the startup allowance increase. The image, context limit, and sequence limit stay the same.
-->

---
layout: your-turn
lesson: 02-tensor-parallel
steps: Steps 3 to 5
minutes: 7
---

## Inspect Both GPUs, Then Stream a Reply

Look for:

<v-clicks>

- TP ranks 0 and 1 and the KV cache size in the logs
- Model memory in use on both GPUs
- The model reasons before it answers

</v-clicks>


<!--
Each GPU's memory use exceeds its weight shard because each also holds runtime buffers and KV cache.
-->
