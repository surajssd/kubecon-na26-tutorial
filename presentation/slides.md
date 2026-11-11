---
theme: default
title: Minting Your Own Tokens
titleTemplate: '%s'
info: Interactive Inference 101 for KubeCon NA 2026.
favicon: false
colorSchema: auto
transition: fade
selectable: true
fonts:
  provider: none
  sans: Roboto Variable
  mono: Menlo
layout: kubecon-title
class: title-slide
---

<p class="kicker">Interactive Inference 101</p>

# Minting Your Own Tokens

<p class="lede">The server side of the token economy</p>

<div class="speakers">
  <p><strong>Suraj Deshmukh</strong><img class="speaker-company-logo" src="./assets/companies/coreweave-white.svg" alt="CoreWeave"></p>
  <p><strong>Nilekh Chaudhari</strong><img class="speaker-company-logo" src="./assets/companies/microsoft-white.svg" alt="Microsoft"></p>
</div>

<!--
We will deploy model servers on Kubernetes and follow a request from its prompt to its generated tokens. Each lesson changes how the work is shared across GPUs.
-->

---
layout: chapter
---

<Speakers />

---
layout: center
class: slides-link
---

# Slides

<img class="slides-qr" src="./assets/slides-qr.svg" alt="QR code for https://suraj.io/kubecon-na26" width="300" height="300">

<a class="slides-url" href="https://suraj.io/kubecon-na26" target="_blank">suraj.io/kubecon-na26</a>

<style>
.slides-link { text-align: center; }
.slides-link .slides-qr { display: block; width: 300px; height: 300px; margin: 20px auto; }
.slides-link .slides-url { font-size: 1.6rem; font-weight: 700; color: var(--ink); }
</style>

---
src: ./slides/01-intro.md
---

---
src: ./slides/02-single-gpu.md
---

---
src: ./slides/03-batching-memory-tp.md
---

---
src: ./slides/04-pipeline-parallel.md
---

---
src: ./slides/05-disaggregation.md
---

---
src: ./slides/06-performance.md
---

---
src: ./slides/07-recap.md
---

---
layout: chapter
---

<Speakers />

<!--
These QR codes link to our profiles if you would like to follow up after the session.
-->
