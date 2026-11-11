<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ step?: number }>(), { step: 0 })
const current = computed(() => Math.min(Math.max(props.step, 0), 6))
const summaries = [
  'Token xₜ is ready at the leader. Advance to start layer 1.',
  'GPU 0 computes layer 1. GPU 1 waits for activations.',
  'GPU 0 computes layer 2. No transfer between GPUs within this stage.',
  'Transfer intermediate activations from stage 0 to stage 1.',
  'GPU 1 computes layer 3. GPU 0 waits for the next token.',
  'GPU 1 computes layer 4. The token has passed through every layer.',
  'Output head and sampling produce xₜ₊₁. Repeat for the next token.',
]
</script>

<template>
  <figure class="pp" :data-step="current" aria-label="Pipeline parallelism: one token passes through four layers, with an activation transfer between stages">
    <div class="service">Service <code>vllm-leader</code> → leader only</div>
    <p class="flow-label">One decode step · 4 illustrative layers · input xₜ</p>
    <div class="nodes">
      <div class="node">
        <p class="node-label">Node A · Pod <code>vllm-0</code> · leader</p>
        <div class="gpu">
          <p class="gpu-label"><GpuIcon width="18" height="18" /> GPU 0 · PP stage 0 · serves HTTP</p>
          <div class="stack first">
            <div v-for="layer in [1, 2]" :key="layer" class="layer" :class="{ active: current === layer, done: current > layer }">Layer {{ layer }}</div>
            <span class="token-state" :class="{ visible: current === 1 || current === 2 }" :style="{ transform: `translateY(${current >= 2 ? 38 : 0}px)` }" aria-hidden="true" />
          </div>
          <p class="gpu-status">{{ current === 1 || current === 2 ? 'Computing' : 'Waiting' }}</p>
        </div>
      </div>
      <div class="link" :class="{ active: current === 3 }">
        <span class="arrow">→</span>
        <span v-if="current === 3" class="transfer-state" aria-hidden="true" />
        <p>activations once per stage boundary, over the network</p>
      </div>
      <div class="node">
        <p class="node-label">Node B · Pod <code>vllm-0-1</code> · worker</p>
        <div class="gpu">
          <p class="gpu-label"><GpuIcon width="18" height="18" /> GPU 1 · PP stage 1 · <code>--headless</code></p>
          <div class="stack second">
            <div v-for="layer in [3, 4]" :key="layer" class="layer" :class="{ active: current === layer + 1, done: current > layer + 1 }">Layer {{ layer }}</div>
            <span class="token-state" :class="{ visible: current === 4 || current === 5 }" :style="{ transform: `translateY(${current >= 5 ? 38 : 0}px)` }" aria-hidden="true" />
          </div>
          <p class="gpu-status">{{ current === 6 ? 'Stage complete' : current === 4 || current === 5 ? 'Computing' : 'Waiting' }}</p>
        </div>
      </div>
    </div>
    <p class="output" :class="{ ready: current === 6 }" :aria-hidden="current !== 6">Next token xₜ₊₁</p>
    <figcaption aria-live="polite"><strong>{{ current }}/6</strong> {{ summaries[current] }}</figcaption>
  </figure>
</template>

<style scoped>
.pp {
  margin: 0;
}

.service {
  width: fit-content;
  margin-bottom: 8px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.72rem;
  color: var(--ink-muted);
}

.nodes {
  display: grid;
  grid-template-columns: 1fr 120px 1fr;
  align-items: center;
}

.node {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
}

.node-label,
.gpu-label {
  margin: 0 0 6px;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--ink-muted);
}

.stack {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  justify-content: center;
  height: 84px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--ink);
}

.stack.first { --req: var(--req-1); }
.stack.second { --req: var(--req-2); }

.layer {
  width: 100%;
  height: 32px;
  line-height: 30px;
  text-align: center;
  border: 1px solid var(--req);
  border-radius: 5px;
  background: color-mix(in srgb, var(--req) 15%, transparent);
  transition: background-color 0.3s, opacity 0.3s;
}
.layer.active { background: var(--req); color: var(--ink-inverse); }
.layer.done { opacity: 0.55; }

.gpu-label { display: flex; align-items: center; gap: 4px; }
.gpu-status { margin: 4px 0 0; min-height: 1.5em; font-size: 0.7rem; text-align: center; }
.flow-label { margin: 0 0 8px; font-size: 0.72rem; }
.output { margin: 4px 0; min-height: 1.5em; font-size: 0.72rem; text-align: right; opacity: 0; }
.output.ready { opacity: 1; color: var(--live); }

.token-state,
.transfer-state {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 2px solid var(--ink-inverse);
  border-radius: 50%;
  background: var(--ink);
}
.token-state { top: 17px; left: 12px; opacity: 0; transition: transform 0.45s ease, opacity 0.3s; }
.token-state.visible { opacity: 1; }
.transfer-state { top: 12px; left: calc(50% - 7px); animation: transfer 0.65s ease both; }

.link {
  position: relative;
  text-align: center;
}
.link .arrow { opacity: 0.3; }
.link.active .arrow { opacity: 1; }

.arrow {
  font-size: 2rem;
  color: var(--accent);
}

.link p {
  margin: 0;
  font-size: 0.62rem;
  line-height: 1.25;
  color: var(--ink-muted);
}

figcaption {
  margin-top: 8px;
  min-height: 1.5em;
  font-size: 0.78rem;
  color: var(--ink-muted);
}

@keyframes transfer {
  from { transform: translateX(-45px); }
  to { transform: translateX(45px); }
}

@media (prefers-reduced-motion: reduce) {
  .layer, .token-state { transition: none; }
  .transfer-state { animation: none; }
}
</style>
