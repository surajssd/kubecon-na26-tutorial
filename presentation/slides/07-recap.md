---
layout: two-cols
class: ladder-slide
---

<p class="kicker">Recap</p>

# You Climbed the Ladder

<v-clicks>

- **1:** weights, runtime, and KV cache share one GPU budget. Batching serves many requests per step.
- **2:** tensor parallelism splits every layer. Our Pod requested two GPUs on one node.
- **3:** pipeline parallelism splits the layers into stages. LeaderWorkerSet runs it across nodes.
- **4:** disaggregation splits the request by phase. The KV cache moves between GPUs.

</v-clicks>

::right::

<DeploymentLadder class="ladder-big" :current="5" :revealed="$clicks" />

<style>
.ladder-slide .ladder-big { margin-top: 70px; }
</style>

<!--
We changed how one model uses GPUs: one GPU, tensor parallelism, then pipeline parallelism across nodes. Disaggregation then changed the split to prefill and decode, using a different model and serving system.

Memory capacity, communication between GPUs, and the workload all affect which setup is useful. The traffic runs and dashboards give us evidence about this workshop's configurations.
-->

---

<p class="kicker">Evidence and operational guidance</p>

# What You Saw for Yourself

<div class="checklist">
  <div v-click="1" class="card"><span class="check">✓</span><div><h2>LLM servers cache aggressively</h2><p>The KV cache holds keys and values for every processed token. Its capacity is in tokens, not requests: about 3 full sequences fit where 8 were allowed.</p></div></div>
  <div v-click="2" class="card"><span class="check">✓</span><div><h2>Batching increased completed work</h2><p>Concurrency 4 finished more requests than 1. For capacity decisions, inspect queues and latency alongside GPU activity.</p></div></div>
  <div v-click="3" class="card"><span class="check">✓</span><div><h2>GPU placement changes what can run</h2><p>Our TP Pod needed two GPUs on one node. Our PP group required two nodes. Fast links reduce communication overhead.</p></div></div>
</div>

<style>
.checklist { display: flex; flex-direction: column; gap: 12px; margin-top: 14px; }
.checklist .card { display: flex; gap: 16px; align-items: center; }
.check { font-size: 2rem; font-weight: 800; color: var(--live); }
.checklist h2 { margin: 0; }
</style>

---
layout: chapter
class: closing
---

<div class="closing-grid">
  <div>
    <p class="kicker">Thank you</p>
    <h1>Questions?</h1>
    <div v-click="1" class="closing-topics">
      <h2>Next topics</h2>
      <ul>
        <li v-click="1">Quantization (FP8, NVFP4)</li>
        <li v-click="2">Expert parallelism</li>
        <li v-click="3">Tool calling</li>
        <li v-click="4">Goodput targets</li>
      </ul>
    </div>
  </div>
  <div v-click="5" class="closing-feedback">
    <h2>Session feedback</h2>
    <p>Scan to share your feedback.</p>
    <img src="../assets/session-feedback.png" alt="QR code for session feedback" width="300" height="300">
  </div>
</div>

<style>
.closing :deep(.chapter-body) { width: 100%; }
.closing-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 32px; align-items: center; margin-top: 48px; }
.closing-topics { margin-top: 24px; text-align: left; }
.closing-feedback { text-align: center; }
.closing-feedback p { margin: 0 0 12px; }
.closing-feedback img { display: block; width: 300px; height: 300px; }
</style>
