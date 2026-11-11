---
layout: center
class: hook
---

<p class="kicker">Live</p>

# Watch the First Token

<p class="lede">A model server on one GPU in this cluster streams a reply.</p>

<div class="cols-3 hook-cards">
  <div v-click="1" class="card"><h2>Time to first token</h2><p>How long until text starts</p></div>
  <div v-click="2" class="card"><h2>One token at a time</h2><p>The reply grows token by token</p></div>
  <div v-click="3" class="card"><h2>Output rate</h2><p>Tokens per second, including the wait</p></div>
</div>

<style>
.hook-cards { margin-top: 28px; text-align: left; }
</style>

<!--
This reply comes from a model server running on one GPU in this cluster. The prompt is "Explain Kubernetes in one sentence."

Time to first token is the wait before text starts to arrive. The token count tells us how much output the model generated. The output rate includes the initial wait.

By the end of today, you will deploy this yourself and know what each of these numbers means.
-->

---

<p class="kicker">While we talk</p>

# Sign In to Your Workspace

<div class="signin">
<div>

1. Open this link, or scan the QR code:<br><a class="workspace-link" href="https://bit.ly/kubecon-na26" target="_blank">bit.ly/kubecon-na26</a>
2. Sign in with GitHub.
3. Open a terminal. It starts in the `tutorial/` folder.

<div class="card">
<h2>Expected result</h2>
<p>VS Code runs in your browser with the <code>tutorial</code> folder open.</p>
<p>The lessons are <code>01-vllm</code> to <code>04-prefill-disaggregation</code>.</p>
</div>

</div>
<img class="workspace-qr" src="../assets/workspace-qr.svg" alt="QR code for https://marimo.cw0bec-kcna26-1111.coreweave.app/" width="210" height="210">
</div>

<style>
.signin { display: grid; grid-template-columns: 1fr 210px; gap: 36px; align-items: start; }
.signin ol { margin-top: 0; }
.signin .workspace-link { display: inline-block; margin-top: 4px; font-family: var(--mono); font-size: 1.2rem; font-weight: 700; color: var(--ink); }
.signin .card { margin-top: 14px; }
.signin .workspace-qr { width: 210px; height: 210px; }
</style>

<!--
Your workspace runs VS Code in the browser. Its terminal starts in the `tutorial/` folder, with all four lessons available.
-->

---

<p class="kicker">What we will explore</p>

# Key Considerations for Serving Models in Production

<div class="cols-3 claims">
  <div v-click="1" class="card"><span class="big-number">1</span><h2>KV cache avoids repeated work</h2><p>The KV cache stores every token a request has processed.</p></div>
  <div v-click="2" class="card"><span class="big-number">2</span><h2>How much work can one server do?</h2><p><strong>Concurrency</strong> is how many requests are open at the same time. Run 1, then 4, and count how many finish in one minute.</p></div>
  <div v-click="3" class="card"><span class="big-number">3</span><h2>GPUs are not fungible</h2><p>Which GPUs a model gets, and how they connect, changes what runs.</p></div>
</div>

<p v-click="3">We return to this list at the end.</p>

<style>
.claims { margin: 18px 0 14px; }
.claims .big-number { color: var(--accent); }
.claims h2 { margin-top: 8px; line-height: 1.2; }
</style>

<!--
The labs compare concurrency and GPU placement. The KV cache avoids repeated work, and batching lets several requests share a model step. Queue depth and latency help us assess capacity, although this tutorial does not demonstrate autoscaling.

Concurrency 4 means the traffic client always keeps four requests open. When one finishes, it sends the next one. It is not four requests in total.
-->

---
layout: two-cols
class: ladder-slide
---

<p class="kicker">The plan for today</p>

# Climb the Deployment Ladder

Each lesson changes how the model is placed on GPUs. Lesson 4 also changes the model and the serving system.

<v-clicks>

- **1:** one model, one GPU
- **2:** one model split across two GPUs in one node
- **3:** one model split across two nodes
- **4:** reading the prompt and writing the reply on separate GPUs

</v-clicks>

<p v-click>Your GPU quota is <strong>2</strong>. Delete each lesson before you start the next one.</p>

::right::

<DeploymentLadder class="ladder-big" :revealed="$clicks" />

<style>
.ladder-slide .ladder-big { margin-top: 70px; }
</style>

<!--
We begin with one model on one GPU. Then we split a larger model across two GPUs, first on one node and then across two nodes. Finally, we give prefill and decode separate GPUs, with a different model and serving system.

Each workload namespace has a quota of two GPUs. Kubernetes checks quota before scheduling, so resources left over from one lesson can block the next one.
-->

---

<p class="kicker">While we talk</p>

# Sign In to Your Workspace

<div class="signin">
<div>

1. Open this link, or scan the QR code:<br><a class="workspace-link" href="https://bit.ly/kubecon-na26" target="_blank">bit.ly/kubecon-na26</a>
2. Sign in with GitHub.
3. Open a terminal. It starts in the `tutorial/` folder.

<div class="card">
<h2>Expected result</h2>
<p>VS Code runs in your browser with the <code>tutorial</code> folder open.</p>
<p>The lessons are <code>01-vllm</code> to <code>04-prefill-disaggregation</code>.</p>
</div>

</div>
<img class="workspace-qr" src="../assets/workspace-qr.svg" alt="QR code for https://marimo.cw0bec-kcna26-1111.coreweave.app/" width="210" height="210">
</div>

<style>
.signin { display: grid; grid-template-columns: 1fr 210px; gap: 36px; align-items: start; }
.signin ol { margin-top: 0; }
.signin .workspace-link { display: inline-block; margin-top: 4px; font-family: var(--mono); font-size: 1.2rem; font-weight: 700; color: var(--ink); }
.signin .card { margin-top: 14px; }
.signin .workspace-qr { width: 210px; height: 210px; }
</style>

<!--
Your workspace runs VS Code in the browser. Its terminal starts in the `tutorial/` folder, with all four lessons available.
-->

---

<p class="kicker">Before you type anything</p>

# How Your Workspace Works

<div class="cols workspace-cards">
<div v-click="1" class="card">

## Where things run

<v-clicks at="1">

- You get your own **workload namespace**. Your model runs there.
- `localhost` is your workspace, not your laptop.
- Models are read-only at `/models`. Nothing downloads.

</v-clicks>

</div>
<div v-click="4" class="card">

## How you work

<v-clicks at="4">

- Keep **one terminal** for all lessons. The commands assume it.
- Copy every command from the lesson README.
- When a step fails, raise your hand.

</v-clicks>

</div>
</div>

<style>
.workspace-cards { margin-top: 18px; align-items: stretch; }
.workspace-cards ul { margin-bottom: 0; padding-left: 1.2rem; }
</style>

<!--
`VLLM_BASE_URL` points to the model's Service in your workload namespace. `localhost` refers to your workspace, so opening that address on a laptop reaches a different machine.

The terminal inherits `NAMESPACE` from the workspace. An empty value means an organizer needs to update and recreate the workspace. Keeping one terminal across lessons preserves its directory and environment variables.
-->
