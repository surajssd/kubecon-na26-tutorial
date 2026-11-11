<script setup lang="ts">
import { computed } from 'vue'
import podIcon from '../assets/icons/pod.svg'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })

// Step 0 shows every step. Steps 1 to 9 follow the request flow in the Dynamo v1.6.0 architecture page. Backticks mark code.
const captions: { topic?: string, text: string }[] = [
  { text: 'Lesson 4 runs three Pods: the frontend, one prefill worker, and one decode worker. Each click follows one chat request through the nine steps in the Dynamo documentation.' },
  { topic: 'Request:', text: 'the demo sends a chat request to the frontend, an OpenAI-compatible server on port 8000, through Service `vllm-frontend`.' },
  { topic: 'Preprocess:', text: 'the frontend applies the chat template, tokenizes the prompt, and validates the request.' },
  { topic: 'Route to prefill:', text: 'the prefill router inside the frontend picks a prefill worker. Lesson 4 has one.' },
  { topic: 'Prefill:', text: 'the prefill worker runs the whole prompt through the model and stores the KV cache in its GPU memory.' },
  { topic: 'Return metadata:', text: 'the prefill worker returns `disaggregated_params`, which say where its KV blocks are.' },
  { topic: 'Route to decode:', text: 'the router adds the transfer metadata to the request and sends it to the decode worker.' },
  { topic: 'KV transfer:', text: 'the decode worker fetches the KV cache from the prefill worker with NIXL. Lesson 4 copies it through CPU buffers over TCP, even when both Pods share a node.' },
  { topic: 'Decode:', text: 'the decode worker generates output tokens from the transferred KV cache.' },
  { topic: 'Response:', text: 'the tokens stream back through the frontend, which detokenizes them, to the demo.' },
]
const lastStep = captions.length - 1
const current = computed(() => Math.min(Math.max(props.step, 0), lastStep))
const caption = computed(() => ({
  topic: captions[current.value].topic,
  parts: captions[current.value].text.split('`').map((text, index) => ({ text, code: index % 2 === 1 })),
}))

interface Box { id: string, title: string, sub?: string, x: number, y: number, w: number, h: number, steps: number[], inner?: boolean, pod?: boolean, gpu?: boolean }
const iconSize = 24
const boxes: Box[] = [
  { id: 'client', title: 'Client', sub: 'streaming demo', x: 20, y: 18, w: 170, h: 70, steps: [1, 9] },
  { id: 'frontend', title: 'Frontend', sub: 'frontend Pod · CPU · OpenAI API on port 8000', x: 330, y: 0, w: 340, h: 140, steps: [2, 9], pod: true },
  { id: 'router', title: 'PrefillRouter', sub: 'runs inside the frontend', x: 350, y: 76, w: 300, h: 50, steps: [3, 6], inner: true },
  { id: 'prefill', title: 'Prefill worker', sub: 'prefill Pod · 1 GPU · full model', x: 40, y: 196, w: 330, h: 116, steps: [4, 5], pod: true, gpu: true },
  { id: 'prefill-kv', title: 'KV cache', sub: 'GPU memory', x: 60, y: 252, w: 150, h: 46, steps: [4, 7], inner: true },
  { id: 'decode', title: 'Decode worker', sub: 'decode Pod · 1 GPU · full model', x: 630, y: 196, w: 330, h: 116, steps: [7, 8], pod: true, gpu: true },
  { id: 'decode-kv', title: 'KV cache', sub: 'GPU memory', x: 650, y: 252, w: 130, h: 46, steps: [7, 8], inner: true },
  { id: 'tokens', title: 'Output tokens', x: 820, y: 252, w: 120, h: 46, steps: [8, 9], inner: true },
]

interface Arrow { step: number, d: string, label?: { text: string, x: number, y: number, anchor?: 'start' | 'middle' | 'end' } }
const arrows: Arrow[] = [
  { step: 1, d: 'M 190 40 H 330', label: { text: 'request', x: 260, y: 32, anchor: 'middle' } },
  { step: 3, d: 'M 380 126 V 166 H 180 V 196', label: { text: 'route', x: 280, y: 160, anchor: 'middle' } },
  { step: 5, d: 'M 300 196 V 182 H 420 V 126', label: { text: 'metadata', x: 428, y: 160 } },
  { step: 6, d: 'M 600 126 V 166 H 780 V 196', label: { text: 'route', x: 690, y: 160, anchor: 'middle' } },
  { step: 7, d: 'M 210 275 H 650', label: { text: 'KV cache · NIXL over TCP', x: 500, y: 266, anchor: 'middle' } },
  { step: 8, d: 'M 780 275 H 820' },
  { step: 9, d: 'M 880 252 V 104 H 670', label: { text: 'tokens', x: 888, y: 180 } },
  { step: 9, d: 'M 330 70 H 190', label: { text: 'response', x: 260, y: 84, anchor: 'middle' } },
]

const badges: { step: number, x: number, y: number }[] = [
  { step: 1, x: 222, y: 40 },
  { step: 2, x: 640, y: 22 },
  { step: 3, x: 230, y: 166 },
  { step: 4, x: 80, y: 275 },
  { step: 5, x: 360, y: 182 },
  { step: 6, x: 740, y: 166 },
  { step: 7, x: 430, y: 275 },
  { step: 8, x: 800, y: 293 },
  { step: 9, x: 880, y: 150 },
  { step: 9, x: 222, y: 70 },
]

// At step 0 every step is drawn as done. Later, a step is done, current, or still to come.
const stateOf = (step: number) => current.value === 0 || step < current.value ? 'done' : step === current.value ? 'now' : 'later'

const boxViews = computed(() => boxes.map(box => ({ ...box, lit: current.value > 0 && box.steps.includes(current.value) })))
const arrowViews = computed(() => arrows.map((arrow, index) => ({ ...arrow, key: index, state: stateOf(arrow.step) })))
const badgeViews = computed(() => badges.map((badge, index) => ({ ...badge, key: index, state: stateOf(badge.step) })))
</script>

<template>
  <div class="dynamo-flow">
    <p class="kicker">NVIDIA Dynamo · lesson 4</p>
    <h1>One Request Through Dynamo</h1>
    <svg viewBox="0 0 1000 316" role="img" aria-label="Dynamo request flow in lesson 4: the client calls the frontend, the prefill router sends the request to the prefill worker, the prefill worker returns transfer metadata, the router sends the request to the decode worker, the decode worker fetches the KV cache through NIXL, generates tokens, and streams them back through the frontend.">
      <defs>
        <marker id="dynamo-flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="arrow-head" />
        </marker>
        <marker id="dynamo-flow-arrow-now" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" class="arrow-head now" />
        </marker>
      </defs>

      <g v-for="box in boxViews" :key="box.id" class="box-group" :class="[box.id, { inner: box.inner, lit: box.lit }]">
        <rect class="box" :x="box.x" :y="box.y" :width="box.w" :height="box.h" rx="10" />
        <template v-if="box.inner">
          <text class="box-title" :x="box.x + box.w / 2" :y="box.y + (box.sub ? 20 : 28)" text-anchor="middle">{{ box.title }}</text>
          <text v-if="box.sub" class="box-sub" :x="box.x + box.w / 2" :y="box.y + 37" text-anchor="middle">{{ box.sub }}</text>
        </template>
        <template v-else>
          <image v-if="box.pod" :href="podIcon" :x="box.x + 12" :y="box.y + 9" :width="iconSize" :height="iconSize" />
          <GpuIcon v-if="box.gpu" :x="box.x + box.w - 36" :y="box.y + 10" :width="iconSize" :height="iconSize" />
          <text class="box-title" :x="box.x + (box.pod ? 44 : 16)" :y="box.y + 26">{{ box.title }}</text>
          <text v-if="box.sub" class="box-sub" :x="box.x + (box.pod ? 44 : 16)" :y="box.y + 46">{{ box.sub }}</text>
        </template>
      </g>

      <g v-for="arrow in arrowViews" :key="arrow.key" class="arrow" :class="arrow.state">
        <path :d="arrow.d" :marker-end="arrow.state === 'now' ? 'url(#dynamo-flow-arrow-now)' : 'url(#dynamo-flow-arrow)'" />
        <text v-if="arrow.label" :x="arrow.label.x" :y="arrow.label.y" :text-anchor="arrow.label.anchor ?? 'start'">{{ arrow.label.text }}</text>
      </g>

      <g v-for="badge in badgeViews" :key="badge.key" class="badge" :class="badge.state">
        <circle :cx="badge.x" :cy="badge.y" r="11" />
        <text :x="badge.x" :y="badge.y + 4.5" text-anchor="middle">{{ badge.step }}</text>
      </g>
    </svg>

    <div class="infra">
      <span><strong>Discovery</strong> Kubernetes: workers register, and the frontend watches for them</span>
      <span><strong>Request plane</strong> TCP</span>
      <span><strong>Event plane</strong> ZMQ</span>
    </div>

    <p class="caption" aria-live="polite">
      <span class="step">{{ current === 0 ? 'Request flow' : `Step ${current} of ${lastStep}` }}</span>
      <span><strong v-if="caption.topic">{{ `${caption.topic} ` }}</strong><template v-for="(part, index) in caption.parts" :key="index"><code v-if="part.code">{{ part.text }}</code><template v-else>{{ part.text }}</template></template></span>
    </p>
    <p class="source">Adapted from the request flow in the Dynamo v1.6.0 architecture documentation, docs.nvidia.com/dynamo (Apache-2.0). Pod icon: Kubernetes icon set.</p>
  </div>
</template>

<style scoped>
.dynamo-flow {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.dynamo-flow h1 {
  margin: 2px 0 10px;
}

.dynamo-flow > svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.box {
  fill: var(--surface-raised);
  stroke: var(--line);
  stroke-width: 1.5;
  transition: stroke 0.3s, stroke-width 0.3s;
}

.inner .box {
  fill: rgb(var(--tint) / 0.06);
}

.frontend .box { stroke: var(--req-6); }
.prefill .box { stroke: var(--req-1); }
.decode .box { stroke: var(--req-2); }

.lit .box {
  stroke: var(--accent);
  stroke-width: 2.5;
}

.box-title {
  font-size: 16px;
  font-weight: 700;
  fill: var(--ink);
}

.inner .box-title {
  font-size: 14px;
}

.box-sub {
  font-size: 12px;
  fill: var(--ink-muted);
}

.arrow path {
  fill: none;
  stroke: var(--ink-muted);
  stroke-width: 2;
  transition: stroke 0.3s, opacity 0.3s;
}

.arrow text {
  font-size: 12px;
  fill: var(--ink-muted);
}

.arrow.later {
  opacity: 0.25;
}

.arrow.now path {
  stroke: var(--accent);
  stroke-width: 3;
  stroke-dasharray: 7 5;
  animation: flow 0.8s linear infinite;
}

.arrow.now text {
  font-weight: 700;
  fill: var(--ink);
}

@keyframes flow {
  to { stroke-dashoffset: -12; }
}

.arrow-head {
  fill: var(--ink-muted);
}

.arrow-head.now {
  fill: var(--accent);
}

.badge circle {
  fill: var(--surface-raised);
  stroke: var(--ink-muted);
  stroke-width: 1.5;
}

.badge text {
  font-size: 12px;
  font-weight: 800;
  fill: var(--ink);
}

.badge.later {
  opacity: 0.3;
}

.badge.now circle {
  fill: var(--accent);
  stroke: var(--accent);
}

.badge.now text {
  fill: var(--accent-ink);
}

.infra {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-top: 6px;
  font-size: 0.66rem;
  color: var(--ink-muted);
}

.infra span {
  padding: 2px 8px;
  border: 1px dashed var(--line);
  border-radius: 6px;
}

.infra strong {
  margin-right: 4px;
}

.caption {
  display: flex;
  align-items: baseline;
  gap: 12px;
  /* Room for two lines with border-box sizing, so the box keeps one size across steps. */
  min-height: 4.1em;
  margin: auto 0 0;
  padding: 7px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--ink);
}

.caption .step {
  flex: none;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}

.source {
  margin: 6px 0 -14px;
  font-size: 0.5rem;
  line-height: 1.2;
  color: var(--ink-faint);
}

@media (prefers-reduced-motion: reduce) {
  .arrow.now path { animation: none; }
}
</style>
