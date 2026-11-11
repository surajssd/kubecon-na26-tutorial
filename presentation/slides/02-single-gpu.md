---
layout: your-turn
lesson: 01-vllm
steps: Steps 1 and 2
minutes: 1
---

## Deploy the Model Now, Then Follow Its Logs

Leave the logs running. The model needs about two minutes to load. We explain what you see while it loads.

<!--
The model needs time to load before it can accept requests. In the scale test with 32 attendees, lesson 1 took about 105 seconds to become ready. The logs may be unavailable while the Pod is still starting.
-->

---
layout: chapter
lesson: 1
---

# One Model on One GPU

While Qwen3.5-0.8B loads: what vLLM is, what it does with a request, and where the GPU memory goes.

<!--
One GPU holds the model weights, runtime allocations, and KV cache. vLLM manages that memory and schedules requests through the model.
-->

---

<p class="kicker">The engine you just deployed</p>

# What Is vLLM?

<img class="vllm-logo vllm-logo-light" src="../assets/companies/vllm.svg" alt="vLLM">
<img class="vllm-logo vllm-logo-dark" src="../assets/companies/vllm-dark.svg" alt="vLLM">

<div class="cols vllm-intro">
<div>

<v-clicks>

- vLLM is an open-source **inference engine**. It loads a model onto GPUs and generates tokens for many requests at once.
- It started at UC Berkeley with **[PagedAttention](https://arxiv.org/abs/2309.06180)**: it stores the KV cache in fixed-size blocks, like memory pages.
- One command, `vllm serve`, starts an **OpenAI-compatible API**. Your Pod runs that command.

</v-clicks>

</div>
<div v-click="4" class="card">
<h2>Engines and frameworks</h2>
<p><strong>Engines</strong> run the model: vLLM, SGLang, TensorRT-LLM.</p>
<p><strong>Frameworks</strong> route requests across many engine instances and scale them: NVIDIA Dynamo, llm-d, AIBrix.</p>
<p>Lessons 1 to 3 run vLLM on its own. Lesson 4 runs vLLM inside Dynamo.</p>
</div>
</div>

<style>
.vllm-logo { position: absolute; top: 20px; right: 40px; width: 180px; height: 90px; object-fit: contain; }
.vllm-logo-dark { display: none; }
:global(html.dark .vllm-logo-light) { display: none; }
:global(html.dark .vllm-logo-dark) { display: block; }
.vllm-intro { margin-top: 18px; }
.vllm-intro .card p + p { margin-top: 0.6rem; }
</style>

<!--
vLLM began in the Sky Computing Lab at UC Berkeley. The PagedAttention paper (SOSP 2023) introduced it: https://arxiv.org/abs/2309.06180. vLLM uses the Apache-2.0 license.

PagedAttention gives a request KV-cache blocks as it needs them, the way an operating system gives a process memory pages. Simulation C in lesson 2 shows these blocks.

OpenAI-compatible means that a client for the OpenAI API also works with this server. Lesson 1 step 3 calls `/v1/models` and `/v1/chat/completions`.

vLLM runs the model. Dynamo coordinates vLLM workers and routes requests between them. We use vLLM on its own in lessons 1 to 3, then add Dynamo in lesson 4.
-->

---

<p class="kicker">Inside the vLLM Pod · lesson 1</p>

# Three Parts Inside `vllm serve`

Each flag in lesson 1's `vllm.yaml` configures one of them.

<div class="vllm-parts">
  <div v-click="1" class="card">
    <h2>API server</h2>
    <p>Accepts HTTP requests. Turns messages into prompt tokens, and output tokens back into text.</p>
    <div class="flags"><code>--port 8000</code><code>--served-model-name</code><code>--reasoning-parser qwen3</code></div>
  </div>
  <span v-click="2" class="arrow">⇄</span>
  <div v-click="2" class="card">
    <h2>Engine core</h2>
    <p><strong>Scheduler:</strong> picks the requests for the next step.</p>
    <p><strong>KV cache manager:</strong> tracks the KV blocks of each request.</p>
    <div class="flags"><code>--max-num-seqs 8</code><code>--max-model-len 2048</code></div>
  </div>
  <span v-click="3" class="arrow">⇄</span>
  <div v-click="3" class="card">
    <h2><GpuIcon width="20" height="20" /> GPU worker</h2>
    <p>One for each GPU. Holds the weights and runs the model's forward pass.</p>
    <div class="flags"><code>/models/Qwen/Qwen3.5-0.8B/…</code><code>--gpu-memory-utilization 0.25</code><code>--enforce-eager</code></div>
  </div>
</div>

<v-click at="4">

> Each step: the scheduler picks requests, the GPU worker runs one forward pass for all of them, and the API server streams the new tokens.

</v-click>

<style>
.vllm-parts { display: grid; grid-template-columns: 1fr 28px 1fr 28px 1fr; gap: 8px; align-items: stretch; margin: 16px 0 14px; }
.vllm-parts h2 { display: flex; align-items: center; gap: 6px; }
.vllm-parts .arrow { align-self: center; font-size: 1.5rem; text-align: center; color: var(--accent); }
.vllm-parts .flags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.vllm-parts .flags code { font-size: 0.7rem; }
</style>

<!--
- **API server:** accepts HTTP on port 8000, applies the chat template, and tokenizes the prompt. Clients send the `--served-model-name` value in the `model` field. `--reasoning-parser qwen3` separates reasoning from the answer, and `--default-chat-template-kwargs` turns thinking off for Qwen. The API server also serves `/health` for the Kubernetes probes and `/metrics` for Grafana.
- **Engine core:** runs in its own process. The scheduler runs at most 8 requests in one step (`--max-num-seqs`). Each request holds at most 2,048 tokens (`--max-model-len`). The KV cache manager tracks which blocks each request holds.
- **GPU worker:** loads the weights from the read-only `/models` mount and runs the model. `--gpu-memory-utilization 0.25` sets its memory budget. `--enforce-eager` skips model compilation.

The startup logs follow the same parts: the GPU worker loads the weights, the engine core sizes the KV cache, and the API server starts on port 8000 last.

With one GPU, the GPU worker runs inside the engine core process. Lessons 2 and 3 set `--distributed-executor-backend mp`, which starts one worker process for each GPU. In lesson 3, `--headless` makes the worker Pod run only GPU workers, without an API server or engine core.

vLLM 0.33.0 sources: [engine core](https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/v1/engine/core.py), [API server side of the engine](https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/v1/engine/async_llm.py), [scheduler](https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/v1/core/sched/scheduler.py), [executor choice](https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/config/parallel.py), [headless workers](https://github.com/vllm-project/vllm/blob/v0.33.0/vllm/entrypoints/cli/serve.py). Overview: https://docs.vllm.ai/en/v0.33.0/design/arch_overview/
-->

---

<p class="kicker">Inference</p>

# Tokens In, Tokens Out

<TokenFlow />

<p class="muted small">Illustrative split. Each model has its own tokenizer.</p>

<v-clicks>

- The server first reads the **whole prompt** in one pass. That pass also makes the first reply token. This is **prefill**.
- Then it writes the rest of the reply **one token per step**. This is **decode**.
- For a dense model, every decode step reads every weight from GPU memory. Serving many requests in one step shares that cost.

</v-clicks>

<!--
Prefill processes the whole prompt and makes the first reply token. Each decode step then adds one more token.

One step can serve many requests. Batching shares the work of reading the weights across those requests, while each request needs memory for its cached tokens.
-->

---
clicks: 5
---

<p class="kicker">Request anatomy</p>

# What One Chat Request Contains

<ChatRequest :step="$clicks">

<v-clicks at="1">

- The server turns `messages` into **prompt tokens**.
- A chat app resends the **whole history** every turn, so prompts grow.
- **Client request:** `"max_tokens": 128` limits new output to 128 tokens.
- **Server configuration:** `--max-model-len 2048` limits prompt and output together to 2,048 tokens.

</v-clicks>

</ChatRequest>

<!--
Each new request includes the earlier questions and answers. Those answers now count as prompt tokens, so the prompt grows with every turn. When the conversation fills the context window, the chat app must drop or summarize older turns.

The client uses `max_tokens` to limit new output. The server uses `--max-model-len` to limit the prompt and output together. A 1,000-token prompt plus up to 128 output tokens uses at most 1,128 of our 2,048-token context window.

In lesson 1, step 3, you will compare `prompt_tokens` and `completion_tokens` in the response's `usage` field.

Lesson 1 disables thinking for Qwen. Muse Glimmer reasons before answering in lessons 2 and 3. Reasoning counts toward the `max_tokens` budget and appears in `completion_tokens`. If reasoning uses up that budget, the response can end with finish_reason "length" before producing an answer.
-->

---
clicks: 3
---

<p class="kicker">GPU memory · lesson 1</p>

# Where One GPU's Memory Goes

<div class="memory">
<StackedBar title="Inside the vLLM budget" :clicks="$clicks" :segments="[{ label: 'Weights', value: 3, tone: 'weights', note: 'loaded first', click: 1 }, { label: 'Runtime', value: 2, tone: 'runtime', note: 'activations, buffers', click: 2 }, { label: 'KV cache', value: 7, tone: 'kv', note: 'gets what is left', click: 3 }]" />
</div>

<v-clicks at="2">

- vLLM loads the weights, measures what a forward pass needs, and gives the rest of the budget to the **KV cache**.
- The KV cache size decides how many tokens the server can hold at once.

</v-clicks>

<p v-click="3" class="muted small">The split inside the budget is illustrative. Read the real numbers in your startup logs.</p>

<style>
.memory { display: flex; flex-direction: column; gap: 16px; margin: 14px 0 12px; }
</style>

<!--
vLLM loads the weights, measures what a forward pass needs, and gives the remaining memory budget to the KV cache.

The weights and runtime allocations reduce the space available for cached tokens. The remaining KV cache capacity limits how many tokens requests can hold together.
-->

---

<p class="kicker">Startup logs</p>

# What to Look for While the Model Loads

<v-clicks>

| Look for | What it tells you |
| --- | --- |
| Model loading and the memory it took | The weights now sit in GPU memory |
| GPU KV cache size, in tokens | How many tokens all requests can hold together |
| Maximum concurrency for 2,048 tokens per request | How many full-length requests fit in that cache |
| The API server starts on port 8000 | The model is ready for requests |

</v-clicks>

<p v-click="4" class="muted small">Later request logs show prompt throughput, generation throughput, and running and waiting requests.</p>

<!--
`Model loading took` reports the memory used in GiB and the loading time in seconds. `GPU KV cache size` reports the token capacity shared by all requests.

`Maximum concurrency` estimates how many full-length requests fit in that cache. In lesson 1, the estimate uses `2,048 tokens per request`. The underlying capacity is a token count, so shorter requests can share the same cache in greater numbers.

`Starting vLLM` gives the API server address on port 8000. The memory and capacity numbers depend on the GPU and the vLLM version.
-->

---
class: sim-slide
---

<PrefillDecode preset="one" />

<!--
Prefill emits the first output token. Time to first token, or TTFT, ends there. Decode then emits one token per step. Time per output token, or TPOT, measures the average time per additional token after the first.

Processing the whole prompt gives a TTFT of 2.2. Processing it in chunks of four takes three prefill steps and raises TTFT to 4.2. TPOT stays at 1.1 in both cases.

The final decode step emits `<|im_end|>` and ends the assistant response. This stop token counts as the seventh output token.

All timing values use simulated time units from the teaching model. They are not GPU measurements.
-->

---
layout: center
class: slides-link
---

# Try the Simulations

<img class="slides-qr" src="../assets/prefill-decode-qr.svg" alt="QR code for https://suraj.io/kubecon-na26/#/18" width="300" height="300">

<a class="slides-url" href="https://suraj.io/kubecon-na26/#/18" target="_blank">suraj.io/kubecon-na26/#/18</a>

<style>
.slides-link { text-align: center; }
.slides-link .slides-qr { display: block; width: 300px; height: 300px; margin: 20px auto; }
.slides-link .slides-url { font-size: 1.6rem; font-weight: 700; color: var(--ink); }
</style>

---
layout: your-turn
lesson: 01-vllm
steps: Steps 3 and 4
minutes: 8
---

## Send Requests, Then Load the Server

Look for:

<v-clicks>

- The time to first token in the demo page
- How many requests finish in one minute at concurrency 1 and 4 (1 or 4 requests open at a time)

</v-clicks>


<!--
Temperature controls randomness when the model chooses each next token. The demo accepts values from 0 to 2.

- At 0, the model selects the most likely token, which makes answers more predictable.
- At 0.7, the demo's default, the model allows moderate variation.
- Higher values, such as 1 or 2, give less likely tokens more chance. Answers become more varied and can become less coherent.

Temperature affects the generated text. Streaming displays that text as it arrives. Temperature does not control the streaming speed.

The workspace sets `NAMESPACE` automatically. An empty value means an organizer needs to update and recreate the workspace.
-->

---

<p class="kicker">Grafana overview · during the traffic runs</p>

# What to Watch

<div class="cols-3 watch">
  <div v-click="1" class="card"><h2>Running and waiting requests</h2><p>How full the batch is, and how much demand is queued.</p></div>
  <div v-click="2" class="card"><h2>KV-cache use</h2><p>How much of the token memory is in use.</p></div>
  <div v-click="3" class="card"><h2>Token throughput</h2><p>Prompt and generation tokens per second.</p></div>
  <div v-click="4" class="card"><h2>Latency</h2><p>Time to first token and end-to-end time.</p></div>
  <div v-click="5" class="card"><h2>GPU activity</h2><p>Your one GPU. The data can lag by one minute.</p></div>
  <div v-click="6" class="card"><h2>Compare 1 and 4</h2><p>Did four concurrent requests finish more work in the same minute?</p></div>
</div>

<style>
.watch { margin-top: 16px; }
</style>

<!--
Running and waiting requests show how much work the server has accepted and how much is queued. KV-cache use shows how much token memory is occupied. Token throughput and latency describe how quickly that work finishes.

The Dynamo frontend row stays empty until lesson 4.

The fixed prompt can reuse cached prefixes, so caching affects this comparison. These runs are observations of the workshop setup rather than a controlled benchmark.
-->
