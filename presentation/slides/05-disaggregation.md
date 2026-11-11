<p class="kicker">Debrief · lesson 3</p>

# Split by Layers: Both GPUs Serve Every Request

<div class="cols">
<div>

<v-clicks at="1">

- Each GPU held half of the layers.
- Only the leader served HTTP.
- Every request went through both stages, for both prefill and decode.

</v-clicks>

</div>
<div v-click="4" class="card">
<h2>Another way to split</h2>
<p>Prefill and decode do different work. Prefill reads many prompt tokens at once. Decode reads one token per request per step.</p>
<p>What if each phase had its own GPU?</p>
</div>
</div>

<!--
In lesson 3, every request passed through both pipeline stages for prefill and decode. Another way to divide the work is to give each phase its own GPU.
-->

---
layout: lesson-transition
problem: A Request Can Be Split by Phase Instead of by Layer
next: 4
---

<v-clicks at="1">

1. Stop the demo with <kbd>Ctrl+C</kbd>, then delete lesson 3:

</v-clicks>

<v-click at="1">

```bash
kubectl delete -f vllm.yaml
```

</v-click>

<v-clicks at="2">

2. Enter lesson 4. Expect `dynamographdeployments`:

</v-clicks>

<v-click at="2">

```bash
cd ../04-prefill-disaggregation
kubectl api-resources --api-group=nvidia.com
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
The scale test measured about 167 seconds to readiness for lesson 4.

A live Dynamo 1.6.0 update can hit quota errors. Reapplying a changed manifest requires deleting the DynamoGraphDeployment first and waiting for GPU quota usage to return to 0/2.
-->

---
layout: chapter
lesson: 4
---

# Disaggregated Prefill and Decode

While Dynamo loads: why prefill and decode get in each other's way, and what it costs to separate them.

<!--
Prefill processes many prompt tokens at once, while decode produces one new token per request per step. Separate workers avoid competition between those phases, but moving the KV cache adds a cost. Each worker also has its own cache capacity limit.
-->

---
class: sim-slide
---

<PrefillDecode preset="busy" />

<!--
On one server, a long prefill slows down every running decode. In the whole-prompt example, r1 stalls twice for about 4.3 time units while the server processes r2's and r3's prompts.

Chunks of eight shorten those stalls to about 1.8, but r2 waits 9.5 for its first token instead of 5.1. Chunking trades one request's TTFT for another's TPOT.

Disaggregation gives each phase its own GPU. The simulation does not model the KV transfer needed between those GPUs.
-->

---
layout: center
class: slides-link
---

# Try the Simulations

<img class="slides-qr" src="../assets/busy-prefill-decode-qr.svg" alt="QR code for https://suraj.io/kubecon-na26/#/49" width="300" height="300">

<a class="slides-url" href="https://suraj.io/kubecon-na26/#/49" target="_blank">suraj.io/kubecon-na26/#/49</a>

<style>
.slides-link { text-align: center; }
.slides-link .slides-qr { display: block; width: 300px; height: 300px; margin: 20px auto; }
.slides-link .slides-url { font-size: 1.6rem; font-weight: 700; color: var(--ink); }
</style>

---
class: sim-slide
clicks: 4
---

<DynamoPlanes :step="$clicks" />

<!--
Dynamo is the layer around the inference engine. It routes requests, scales and places workers, and moves KV state between them.

1. In the control plane, the Dynamo Operator turns a `DynamoGraphDeployment` into runtime resources. The Planner and Grove are optional.
2. The request plane contains the frontend and the prefill and decode workers.
3. The storage and events plane includes KV events, KV block offloading (KVBM), and NIXL.

The router is not a separate container. The frontend Pod has one container, `main`, which runs `python3 -m dynamo.frontend`, and the frontend starts its prefill router in the same process. Dynamo can also run a standalone router, but lesson 4 does not.

Lesson 4's frontend uses the default round-robin router mode, so it does not use KV events to route. The manifest sets `nvidia.com/enable-grove: "false"`. The operator creates Deployments and Services for the three components.
-->

---
class: sim-slide
clicks: 9
---

<DynamoRequestFlow :step="$clicks" />

<!--
In disaggregated serving, the frontend's router sends each request to a prefill worker first, then to a decode worker. The decode worker pulls the KV cache.

The request arrives at the frontend on port 8000. Preprocessing applies the chat template, tokenizes the prompt, and validates the request. The prefill worker builds the KV cache and returns `disaggregated_params`. The router sends the request and transfer metadata to the decode worker, which transfers the cache with NIXL. In lesson 4, that transfer uses UCX over TCP with CPU buffers.

The prefill and decode Pods have no affinity rules, so they can land on one node. They still use TCP there: `UCX_TLS=tcp,cuda_copy` leaves out CUDA IPC, so the KV cache crosses the Pod network. Only the copies between each GPU and its CPU buffer go over PCIe. Without these settings, NIXL selects CUDA IPC on one node and copies GPU to GPU, which on L40 GPUs means PCIe. Lesson 4 avoids the CUDA IPC and RDMA requirements on purpose.
Decode then generates tokens, which stream back through the frontend.

The frontend starts the prefill router only after it discovers both a prefill and a decode worker. Until then, requests get HTTP 503 with "prefill routing ... is still activating".
-->

---
clicks: 6
---

<p class="kicker">Disaggregated serving · lesson 4</p>

# Give Each Phase Its Own GPU

<Disaggregation />

<p v-click="5">Gemma 4 12B IT fits on one L40. Each worker holds a <strong>full copy</strong>.</p>

<blockquote v-click="6"><p>Prefill and decode can scale independently.</p></blockquote>

<!--
In lesson 3 each GPU held different layers. Here each GPU holds the whole model and does a different phase of each request.

NVIDIA Inference Xfer Library (NIXL) moves the KV cache from the prefill worker to the decode worker.

Gemma 4 12B IT in BF16 fits on one L40. Muse Glimmer would need four GPUs in this arrangement, two for each full-model copy.

The prefill worker runs `--disaggregation-mode prefill`. The decode worker runs `--disaggregation-mode decode`. Their `NixlConnector` roles are `kv_producer` and `kv_consumer`, respectively.

The CPU frontend exposes the OpenAI-compatible API and routes requests. Lesson 4 transfers the KV cache with NIXL over UCX using TCP and CPU buffers.
-->

---

# Different Phases Can Use Different Hardware

<figure class="heterogeneous-flow" role="img" aria-label="NVIDIA example: Vera Rubin GPUs handle prefill, transfer the KV cache, and Groq 3 LPX LPU accelerators handle decode">
  <div>
    <p class="heterogeneous-prefill">Prefill</p>
    <h2>Vera Rubin GPUs</h2>
  </div>
  <div class="heterogeneous-transfer">
    <p>KV cache</p>
    <span aria-hidden="true">→</span>
  </div>
  <div>
    <p class="heterogeneous-decode">Decode</p>
    <h2>Groq 3 LPX</h2>
    <p>LPU accelerators</p>
  </div>
</figure>

<blockquote><p>Separate workers let each phase use hardware suited to its workload.</p></blockquote>

<style>
.heterogeneous-flow { display: grid; grid-template-columns: 1fr 160px 1fr; gap: 24px; align-items: start; margin: 80px 0 64px; text-align: center; }
.heterogeneous-flow p { margin: 0; }
.heterogeneous-flow h2 { margin: 10px 0; font-size: 1.6rem; }
.heterogeneous-flow .heterogeneous-prefill { color: var(--req-1); font-weight: 700; }
.heterogeneous-flow .heterogeneous-decode { color: var(--req-2); font-weight: 700; }
.heterogeneous-transfer span { display: block; color: var(--accent); font-size: 3.5rem; line-height: 1; }
</style>

<!--
Our lab uses the same GPU type for both phases. The separation also allows heterogeneous hardware.

NVIDIA describes Vera Rubin handling prefill and transferring the KV cache to Groq 3 LPX for decode. Groq's language processing unit (LPU) is a different accelerator type. That requires runtime support and a compatible KV-cache handoff.

NVIDIA also describes splitting attention and feed-forward work within decode. That is a separate configuration from the prefill/decode split shown here.

Source: NVIDIA, August 24, 2026, https://developer.nvidia.com/blog/how-nvidia-groq-3-lpx-unlocks-ultrafast-interactivity-at-long-context-on-nvidia-vera-rubin/
-->

---

# Lesson 3 to 4: The Config Diff

<div class="config-diff-legend"><span class="config-removed">− Lesson 3</span><span class="config-added">+ Lesson 4</span></div>

<h2 v-click="1">Controller and runtime</h2>

<pre v-click="1" class="config-diff"><code><span class="config-removed">- kind: LeaderWorkerSet</span>
<span class="config-added">+ kind: DynamoGraphDeployment</span>
<span class="config-removed">- command: ["vllm", "serve"]</span>
<span class="config-added">+ command: ["python3", "-m", "dynamo.vllm"]</span></code></pre>

<h2 v-click="2">Model arguments</h2>

<pre v-click="2" class="config-diff"><code><span class="config-removed">- /models/meta-models/Muse-Glimmer-30B/…</span>
<span class="config-added">+ --model /models/google/gemma-4-12B-it/…</span></code></pre>

<p v-click="2" class="small">One CPU frontend routes requests to two GPU workers. Each worker holds a full copy of Gemma.</p>

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
Lesson 4 replaces lesson 3's LeaderWorkerSet with a DynamoGraphDeployment. Each GPU worker runs its own model command. The frontend uses python3 -m dynamo.frontend.

The Dynamo Operator creates one CPU frontend and two GPU workers. The workers no longer split Muse Glimmer's layers. Each holds a full Gemma model and performs one phase of each request. Both workers still use one GPU each, BF16 precision, a 2,048-token context limit, and a sequence limit of 8.

The runtime image also changes: lesson 3 uses vLLM 0.33.0, while lesson 4 uses Dynamo 1.6.0 with bundled vLLM 0.31.0. The model, runtime, and serving setup all change, so these lessons do not isolate the performance effect of disaggregation.
-->

---

# Prefill vs Decode: The Config Diff

<div class="config-diff-legend"><span class="config-removed">− Prefill worker</span><span class="config-added">+ Decode worker</span></div>

<h2 v-click="1">Worker mode</h2>

<pre v-click="1" class="config-diff"><code><span class="config-removed">- --disaggregation-mode prefill</span>
<span class="config-added">+ --disaggregation-mode decode</span></code></pre>

<v-click at="2">

## <code>--kv-transfer-config</code>

</v-click>

<pre v-click="2" class="config-diff"><code><span class="config-context">  {</span>
<span class="config-context">    "kv_connector": "NixlConnector",</span>
<span class="config-removed">-   "kv_role": "kv_producer",</span>
<span class="config-added">+   "kv_role": "kv_consumer",</span>
<span class="config-context">    "kv_buffer_device": "cpu"</span>
<span class="config-context">  }</span></code></pre>

<p v-click="2" class="small">Both workers run together. Prefill creates the KV cache. Decode receives the KV cache and generates tokens.</p>

<style>
.config-diff-legend { display: flex; gap: 28px; margin: 12px 0 16px; font-size: 0.95rem; font-weight: 700; }
.config-removed { color: var(--req-2); }
.config-added { color: var(--req-4); }
.config-context { color: var(--ink-muted); }
.config-diff { margin: 8px 0 14px; padding: 8px 0; border: 1px solid var(--line); border-radius: 8px; background: var(--slidev-code-background); }
.config-diff code { display: block; font-family: var(--mono); font-size: 0.95rem; line-height: 1.5; }
.config-diff span { display: inline-block; width: 100%; padding: 0 14px; }
.config-diff .config-removed { background: color-mix(in srgb, var(--req-2) 10%, transparent); }
.config-diff .config-added { background: color-mix(in srgb, var(--req-4) 10%, transparent); }
</style>

<!--
The prefill and decode workers run at the same time. Their vLLM arguments assign different phases and KV connector roles to the two workers.

Both workers use NixlConnector with CPU transfer buffers. Prefill is the `kv_producer`, and decode is the `kv_consumer`. The mode and connector role must agree. Both workers keep the same model, precision, context limit, KV cache budget, and `--disable-hybrid-kv-cache-manager` setting. Sliding-window attention stays enabled.

The manifest also gives the workers distinct component names, types, and health ports.
-->

---
clicks: 3
---

<p class="kicker">The cost</p>

# Moving the KV Cache Is Not Free

<v-clicks>

- Lesson 4 transfers the KV cache over **TCP with CPU buffers**.
- At low concurrency, transfer overhead can make two separate workers **slower than one combined worker**.
- Disaggregation can help when prefill delays decode and **KV transfer is fast**.

</v-clicks>

<!--
A faster transport, such as RDMA or NVLink, changes the cost of disaggregation. This workshop uses TCP with CPU buffers to avoid RDMA and CUDA IPC requirements. At low concurrency, the transfer overhead can make two separate workers slower than one combined worker.

Lesson 4 sets `UCX_TLS=tcp,cuda_copy`. The KV transfer uses TCP without RDMA or CUDA IPC.

A NIXL startup line does not prove that a transfer worked. The streamed reply and both workers' `generate` counters provide evidence that the request passed through both workers.

With CPU transfer buffers, hybrid KV allocation produces corrupt text in this runtime. Both workers keep `--disable-hybrid-kv-cache-manager`.
-->

---

<p class="kicker">Lesson 4 · startup logs</p>

# A Sequence Limit Is Not a Memory Guarantee

<div class="cols">
<div v-click="1" class="card">
  <p><span class="badge live">vLLM startup output</span></p>
  <p><span class="big-number">2 GiB</span> KV cache per worker</p>
  <p><span class="big-number">≈ 6,240</span> token slots</p>
  <p><span class="big-number">≈ 3.05</span> sequences of 2,048 tokens</p>
</div>
<div>

<v-clicks at="2">

- The same workers allow `--max-num-seqs 8`.
- Only about three full-length sequences fit in the cache.
- Gemma 4 12B mixes sliding-window and full attention. Its startup logs report the KV cache capacity.

</v-clicks>

</div>
</div>

<!--
These are startup values reported by the lesson 4 engine. Each worker's 2 GiB KV cache provides about 6,240 token slots, enough for about 3.05 sequences of 2,048 tokens. A sequence limit of 8 therefore does not guarantee memory for eight full-length requests.

Gemma 4 12B mixes sliding-window and full attention. Your startup logs report the KV cache capacity for your running workers.
-->

---
layout: your-turn
lesson: 04-prefill-disaggregation
steps: Steps 3 to 6
minutes: 7
---

## Check Both Workers, Then Stream a Reply

Look for:

<v-clicks>

- The prefill role in one worker's logs and the decode role in the other's
- Evidence that both workers handled your request
- The frontend row in Grafana

</v-clicks>


<!--
Both workers report prompt tokens for the same request. Adding their prompt token rates would count that work twice, so the rates describe each worker separately.
-->
