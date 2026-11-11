<p class="kicker">Debrief · lesson 2</p>

# Lesson 2 Placed Both GPUs in One Pod

<div class="cols">
<div>

<v-clicks at="1">

- Both GPUs held half of every layer.
- They exchanged data at **every layer**.
- The Pod requested both GPUs, so the scheduler needed **two free GPUs on the same node**.

</v-clicks>

</div>
<div v-click="4" class="card">
<h2>In a busy cluster</h2>
<p>Free GPUs are often spread across nodes: one here, one there. A TP 2 Pod waits even though two GPUs are free.</p>
</div>
</div>

<v-click at="4">

> Can one model use a GPU on each of two nodes?

</v-click>

<!--
TP can span nodes. This lesson's placement constraint comes from the single Pod. Lesson 3 uses PP and required anti-affinity to demonstrate a different placement.
-->

---
layout: lesson-transition
problem: Two Free GPUs Can Be on Different Nodes
next: 3
---

<v-clicks at="1">

1. Stop the demo with <kbd>Ctrl+C</kbd>, then delete lesson 2:

</v-clicks>

<v-click at="1">

```bash
kubectl delete -f vllm.yaml
```

</v-click>

<v-clicks at="2">

2. Enter lesson 3. Expect the `leaderworkersets` resource:

</v-clicks>

<v-click at="2">

```bash
cd ../03-pipeline-parallel
kubectl api-resources --api-group=leaderworkerset.x-k8s.io
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
Lesson 3 had the longest measured load in the scale test, at about 280 seconds.

The lesson 2 Service named `vllm` must be gone: LeaderWorkerSet creates its own headless Service with that name.
-->

---
layout: chapter
lesson: 3
---

# Pipeline Parallelism and Hardware

While the LeaderWorkerSet group loads: what LWS creates, how to split by layers, and why the link between GPUs decides what you can run.

<!--
Pipeline parallelism divides the model's layers into stages. LeaderWorkerSet manages the Pods that run those stages, while their node placement determines the link between them.
-->

---
class: sim-slide
clicks: 5
---

<LeaderWorkerSetFlow :step="$clicks" />

<!--
A LeaderWorkerSet runs groups of Pods. Each group has one leader Pod and its worker Pods, and LWS handles the group as one unit.

For LeaderWorkerSet `vllm`, LWS creates a leaders StatefulSet named `vllm`. That StatefulSet creates leader Pod `vllm-0`. LWS then creates a workers StatefulSet named `vllm-0`, owned by that leader Pod. The workers StatefulSet creates worker Pod `vllm-0-1`.

Additional groups each have their own leader and workers, following the same naming pattern.

Pod `vllm-0` owns StatefulSet `vllm-0`, so deleting the leader Pod also deletes its workers. `RecreateGroupOnPodRestart` uses this to restart the whole group. The workers StatefulSet starts at ordinal 1, so the first worker is `vllm-0-1`.

LWS also creates the headless Service `vllm` for Pod DNS names. Lesson 3 adds Service `vllm-leader` for API requests.
-->

---
clicks: 6
---

<p class="kicker">Pipeline parallelism · lesson 3</p>

# Split the Layers Into Stages

<PipelineParallel :step="$clicks" />

<!--
Stage 0 runs layers 1 and 2, then transfers the activations to stage 1 for layers 3 and 4. The output head and sampling produce the next token. This four-layer example simplifies the real model, and the transfer duration does not predict network latency. Each Pod can see its own physical GPU as device 0 even though it runs a different stage.

Prefill has finished and the prior KV cache is available. The next decode step feeds the sampled token into stage 0. The diagram omits the embedding, attention internals, and return path for the sampled token. LeaderWorkerSet keeps both Pods as one model replica; required anti-affinity puts them on different nodes. [Source](https://developer.nvidia.com/blog/boosting-llama-3-1-405b-throughput-by-another-1-5x-on-nvidia-h200-tensor-core-gpus-and-nvlink-switch/)
-->

---

<p class="kicker">Pipeline parallelism · lesson 3</p>

# How Pipeline Parallelism Works

vLLM: `--pipeline-parallel-size 2` across `--nnodes 2`

<div class="cols">
<div>

<v-clicks at="1">

- A **stage** is a group of consecutive layers on one GPU. Here, stage&nbsp;0 has the first half and stage&nbsp;1 has the second half.
- Stage 0 sends activations to stage 1 once per step.

</v-clicks>

</div>
<div>

<v-clicks at="3">

- One request uses one stage at a time, so PP alone does not make one request faster.
- PP needs less communication than TP, so it tolerates a slower link.

</v-clicks>

</div>
</div>

<!--
Stage 0 runs the first half of the layers, then hands the activations to stage 1. With several requests in flight, both stages can work at once on different requests.

Lesson 3 keeps the same Muse Glimmer checkpoint, so only the parallelism and the node placement change.
-->

---

<p class="kicker">Tensor or pipeline</p>

# When to Use TP or PP

<v-clicks>

| | Tensor parallel · lesson 2 | Pipeline parallel · lesson 3 |
| --- | --- | --- |
| What is split | Every layer, across GPUs | The layers, into stages |
| Communication | At every layer | Once per stage boundary |
| One request | Often lower latency with fast GPU links | Stages run sequentially |
| Total throughput | Communication can limit gains | Can win when concurrent requests keep stages busy |
| When to try | Fast links: NVLink or NVSwitch | Slower links, including across nodes |

</v-clicks>

<v-click at="5">

**Common combination:** TP within each node, PP across nodes.

> Compare latency and total tokens/s. Lessons 2 and 3 also change node placement.

</v-click>

<!--
Neither method is always faster. With TP, GPUs work together within each layer, but synchronization adds overhead. With PP, one request passes through the stages sequentially. During ordinary autoregressive decoding, the next token waits for the previous token. Enough independent requests or microbatches can keep different stages busy at the same time.

When the model, runtime allocations, and required KV cache fit, one GPU is a reasonable starting point. TP on fast GPU links is a candidate for interactive latency. PP is worth benchmarking for throughput on GPUs without NVLink. PP can also run within one node, and TP can span nodes with suitable links. A common larger deployment uses TP within each node and PP across nodes, for example TP 8 and PP 2 on two eight-GPU nodes.

A controlled comparison measures time to first token, time between output tokens, and total output tokens per second. It holds the model, GPU count and type, placement, prompt and output lengths, and concurrency fixed. Lesson 2 uses one Pod with two GPUs on one node. Lesson 3 uses a LeaderWorkerSet with two Pods, one GPU on each of two nodes. Their measurements change both parallelism and placement.

The vLLM logs show 26.11 GiB of model memory per GPU for lesson 2 and 28.56 GiB for lesson 3. These values apply to the pinned model and runtime.

PP uses more memory per GPU than TP. The Muse Glimmer code keeps the full token embedding and the full LM head (2.5 GiB each) on both pipeline stages and splits only the 52 decoder layers. TP splits everything in half.

[Source1](https://developer.nvidia.com/blog/boosting-llama-3-1-405b-throughput-by-another-1-5x-on-nvidia-h200-tensor-core-gpus-and-nvlink-switch/)

[Source 2](https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/)
-->

---
clicks: 5
---

<p class="kicker">LeaderWorkerSet</p>

# One Model Replica, Two Pods

<table class="replica-table">
  <thead>
    <tr><th>Pod</th><th>Pipeline role</th><th>HTTP API</th></tr>
  </thead>
  <tbody>
    <tr v-click="1"><td>Leader <code>vllm-0</code></td><td>Stage 0</td><td>Serves requests</td></tr>
    <tr v-click="2"><td>Worker <code>vllm-0-1</code></td><td>Stage 1</td><td>Runs <code>--headless</code></td></tr>
  </tbody>
</table>

<ul>
  <li v-click="3">Service <code>vllm-leader</code> sends API requests to the leader.</li>
  <li v-click="4">Headless Service <code>vllm</code> provides Pod discovery.</li>
  <li v-click="5">If either Pod restarts, LWS restarts the whole group.</li>
</ul>

<style>
.replica-table { border-collapse: separate; border-spacing: 0; }
</style>

<!--
A Deployment cannot express "these two Pods are one replica". LWS can, and it restarts them together because one stage alone is useless.

The leader has PP rank 0. Both Pods load model weights and allocate KV cache, but only the leader starts the API server.

LWS sets `LWS_GROUP_SIZE` to 2. vLLM uses it for `--pipeline-parallel-size` and `--nnodes`. `LWS_WORKER_INDEX` supplies `--node-rank`: 0 for the leader and 1 for the worker. `LWS_LEADER_ADDRESS` supplies the rendezvous address through `--master-addr`.

The manifest uses `RecreateGroupOnPodRestart`. If either Pod restarts, LWS restarts the whole group so that both stages can recover together.

The `startupPolicy: LeaderCreated` setting lets the worker start after the leader Pod is created. Both stages can initialize before the leader becomes ready. The leader needs the worker before it can finish startup.
-->

---

# Lesson 2 to 3: The Config Diff

<div class="config-diff-legend"><span class="config-removed">− Lesson 2</span><span class="config-added">+ Lesson 3</span></div>

<div class="config-diff-columns">
<div v-click="1">

## vLLM arguments

<pre class="config-diff"><code><span class="config-removed">- --tensor-parallel-size 2</span>
<span class="config-added">+ --tensor-parallel-size 1</span>
<span class="config-added">+ --pipeline-parallel-size $(LWS_GROUP_SIZE)</span>
<span class="config-added">+ --nnodes $(LWS_GROUP_SIZE)</span>
<span class="config-added">+ --node-rank $(LWS_WORKER_INDEX)</span>
<span class="config-added">+ --master-addr $(LWS_LEADER_ADDRESS)</span>
<span class="config-added">+ --headless</span></code></pre>

</div>
<div v-click="2">

## Kubernetes

<pre class="config-diff"><code><span class="config-removed">- kind: Deployment</span>
<span class="config-added">+ kind: LeaderWorkerSet</span>
<span class="config-added">+ size: 2</span>
<span class="config-removed">- nvidia.com/gpu: 2</span>
<span class="config-added">+ nvidia.com/gpu: 1</span></code></pre>

</div>
</div>

<p v-click="2" class="small">Only the worker uses <code>--headless</code>. Required anti-affinity puts the Pods on different nodes.</p>
<p v-click="2" class="muted small">Selected settings. GPU requests and limits change per Pod. The model stays the same.</p>

<style>
.config-diff-legend { display: flex; gap: 28px; margin: 12px 0 16px; font-size: 0.95rem; font-weight: 700; }
.config-diff-columns { display: grid; grid-template-columns: 1.65fr 1fr; gap: 20px; align-items: start; }
.config-removed { color: var(--req-2); }
.config-added { color: var(--req-4); }
.config-diff { margin: 8px 0 14px; padding: 8px 0; border: 1px solid var(--line); border-radius: 8px; background: var(--slidev-code-background); }
.config-diff code { display: block; font-family: var(--mono); font-size: 0.95rem; line-height: 1.5; }
.config-diff span { display: inline-block; width: 100%; padding: 0 14px; }
.config-diff .config-removed { background: color-mix(in srgb, var(--req-2) 10%, transparent); }
.config-diff .config-added { background: color-mix(in srgb, var(--req-4) 10%, transparent); }
</style>

<!--
Lesson 3 replaces the lesson 2 Deployment with a LeaderWorkerSet. The group size belongs to `spec.leaderWorkerTemplate`, and `nvidia.com/gpu` appears in both requests and limits of both Pod templates.

`LWS_GROUP_SIZE` is 2, so pipeline parallelism and the node count are both 2. `LWS_WORKER_INDEX` supplies rank 0 for the leader and rank 1 for the worker. `LWS_LEADER_ADDRESS` gives both Pods the rendezvous address. Only the worker adds `--headless`; the leader keeps its HTTP host and port.

Two GPUs still serve one model replica. Required Pod anti-affinity puts them on different nodes. The model revision, image, BF16 precision, memory budget, context limit, sequence limit, and mp executor stay the same.
-->

---
clicks: 5
class: interconnect-slide
---

<p class="kicker">Claim 3 · hardware</p>

# GPUs Are Not Fungible: The Link Matters

<Interconnects />

<div v-click="5">

Our **L40s use PCIe** and have no NVLink.

> TP exchanges data at every layer. PP sends activations between stages.

</div>

<style>
.interconnect-slide :deep(.slidev-vclick-target) { transition: opacity 0.6s ease-out; }
@media (prefers-reduced-motion: reduce) {
  .interconnect-slide :deep(.slidev-vclick-target) { transition: none; }
}
</style>

<!--
NVLink provides dedicated GPU-to-GPU links. Rack-scale systems such as GB200 NVL72 extend one NVLink domain to 72 GPUs.

Lesson 2's TP traffic between the two L40 GPUs goes over PCIe. Each workshop L40 has 48 GB of GDDR6 memory and no NVLink.

RDMA connects nodes over InfiniBand or RoCE and moves data without CPU copies. TCP/IP connects nodes over ordinary Ethernet through the kernel network stack.

TP exchanges data at every layer, so fast links matter. PP sends activations across stage boundaries and needs less communication, so it can tolerate slower links between nodes.

`nvidia-smi topo -m` shows the PCIe path between GPUs: PIX or PXB means they share a PCIe switch, and PHB, NODE, or SYS means the traffic goes through the CPU. PCIe and one RDMA link have bandwidth in the same range. These examples do not establish the workshop network's RDMA capability.

Hopper systems such as H100 use NVLink inside one machine. Grace Blackwell rack systems extend one NVLink domain across the rack, and their Grace CPU is Arm.
-->

---
layout: your-turn
lesson: 03-pipeline-parallel
steps: Steps 3 to 5
minutes: 6
---

## Inspect Both Stages, Then Stream a Reply

Look for:

<v-clicks>

- PP rank 0 in the leader's logs
- One GPU in each Pod
- Engine metrics in Grafana for the leader only

</v-clicks>


<!--
A running worker does not prove the model is ready. The leader's API startup line confirms that the API server has started.
-->
