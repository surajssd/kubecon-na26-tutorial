<p class="kicker">Clean up lesson 4</p>

# Release Your GPUs

<div class="cols">
<div>

<v-clicks at="1">

1. Stop the demo with <kbd>Ctrl+C</kbd>.
2. Delete the Dynamo deployment:

</v-clicks>

<v-click at="2">

```bash
kubectl delete -f dynamo.yaml --cascade=foreground --timeout=180s
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

</div>
<div v-click="4" class="card">
<p><span class="badge live">Debrief · lesson 4</span></p>
<h2>Prefill and decode ran on separate GPUs</h2>
<p>Both counters went up, and the reply streamed. KV transfer over TCP adds overhead.</p>
<p>Measure the benefit against a combined worker with the same model and workload.</p>
<p><strong>So when does each serving shape pay off?</strong></p>
</div>
</div>

<!--
Deleting the Dynamo deployment releases the GPUs. Quota usage returns to 0/2 after its GPU Pods terminate.
-->

---
layout: chapter
---

# Latency and Throughput

Which number to watch depends on who waits for the answer.

<!--
Chat users wait for text to start and then for each later token. Batch jobs care more about how much output the server finishes over time. The useful metric depends on that workload.
-->

---
clicks: 4
class: metrics-slide
---

<p class="kicker">Definitions</p>

# Four Numbers, Four Questions

<table class="metrics-table">
  <thead>
    <tr><th>Metric</th><th>Question it answers</th><th>Unit</th></tr>
  </thead>
  <tbody>
    <tr v-click="1"><td>Time to first token (TTFT)</td><td>How long until the first token arrives?</td><td>seconds</td></tr>
    <tr v-click="2"><td>Time per output token (TPOT)</td><td>How long does each additional token take, on average?</td><td>seconds/token</td></tr>
    <tr v-click="3"><td>End-to-end latency</td><td>How long until the whole answer finishes?</td><td>seconds</td></tr>
    <tr v-click="4"><td>Output throughput</td><td>How many output tokens does the server produce each second?</td><td>tokens/second</td></tr>
  </tbody>
</table>

<p v-click="4" class="muted small timing-note">These metrics use server timing. Network delay adds to the user's wait.</p>

<style>
.metrics-slide { display: flex; flex-direction: column; }
.metrics-table { border-collapse: separate; border-spacing: 0; }
.metrics-slide .timing-note { margin-top: auto; margin-bottom: 0; }
</style>

<!--
Time to first token (TTFT) measures the wait from when the server receives a request until it sends the first output token:

$t_{\text{first token}} - t_{\text{server receives}}$

Time per output token (TPOT) measures the average time per additional output token after the first:

$\dfrac{t_{\text{last token}} - t_{\text{first token}}}{N_{\text{output tokens}} - 1}$

TPOT excludes the first token, and it is undefined for a one-token reply.

End-to-end latency measures the wait from when the server receives a request until it sends the last output token:

$t_{\text{last token}} - t_{\text{server receives}}$

Output throughput sums the output tokens across all requests and divides by the measurement duration:

$\dfrac{N_{\text{output tokens, all requests}}}{t_{\text{last token, last request}} - t_{\text{server receives, first request}}}$

The throughput window starts when the server receives the first request and ends when it sends the last token across all requests. These definitions are the ones the simulations use.

Chat users need a low TTFT and a TPOT fast enough to keep up with reading. Batch jobs can tolerate more latency, while throughput sets the cost per token.

Goodput counts requests per second that meet explicit TTFT and TPOT targets, combining request latency with completed work.
-->

---
class: sim-slide
clicks: 2
---

<LatencyThroughput :revealed="$clicks" />

<!--
More concurrency raises throughput while there is queued work, but bigger batches make each step slower.

Under heavy load, raising max sequences from 1 to 16 increases throughput until it flattens. Throughput rises from about 0.8 to 2.3 tokens per time unit, while median TPOT rises from about 1.2 to 3.2. Median TTFT falls because less work queues, even though later tokens take longer.

Under light load, throughput stops rising at 4 because requests arrive too slowly to use more capacity. A median also hides the slowest requests, which can have very different waits.

These are simulated time units from a teaching model with explicit coefficients. They do not predict a GPU.
-->

---
layout: center
class: slides-link
---

# Try the Simulations

<img class="slides-qr" src="../assets/latency-throughput-qr.svg" alt="QR code for https://suraj.io/kubecon-na26/#/63" width="300" height="300">

<a class="slides-url" href="https://suraj.io/kubecon-na26/#/63" target="_blank">suraj.io/kubecon-na26/#/63</a>

<style>
.slides-link { text-align: center; }
.slides-link .slides-qr { display: block; width: 300px; height: 300px; margin: 20px auto; }
.slides-link .slides-url { font-size: 1.6rem; font-weight: 700; color: var(--ink); }
</style>

---

<p class="kicker">Live metrics</p>

# Every Source Measures a Different Interval

<v-clicks>

| Source | What it measures |
| --- | --- |
| Demo page | From browser submit to the first reasoning or answer text. Its rate includes that wait. |
| `traffic.py` | Completion tokens of completed requests, divided by the whole run. No TTFT or TPOT. |
| vLLM engine panels | TTFT, inter-token latency, and end-to-end time inside the engine. Percentiles are histogram estimates. |
| Dynamo frontend panels | Client-facing TTFT, latency, and request rate in lesson 4. |

</v-clicks>

<v-click at="4">

> Name the source before you compare two numbers.

</v-click>

<!--
The engine's inter-token latency histogram and the simulator's per-request TPOT aggregate different intervals. Live values describe the running system; simulated values describe the teaching model. A comparison needs the source and measurement interval for each value.
-->
