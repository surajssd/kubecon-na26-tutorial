<script setup lang="ts">
withDefaults(defineProps<{ current?: number, compact?: boolean, revealed?: number }>(), { current: 0, compact: false, revealed: 4 })

const rungs = [
  { lesson: 1, name: 'One GPU', model: 'Qwen3.5-0.8B', shape: 'Deployment', gpus: 1, nodes: 1 },
  { lesson: 2, name: 'Tensor parallel', model: 'Muse Glimmer 30B', shape: 'Deployment, TP 2', gpus: 2, nodes: 1 },
  { lesson: 3, name: 'Pipeline parallel', model: 'Muse Glimmer 30B', shape: 'LeaderWorkerSet, PP 2', gpus: 2, nodes: 2 },
  { lesson: 4, name: 'Disaggregated', model: 'Gemma 4 12B IT', shape: 'Dynamo: prefill + decode, one or two nodes', gpus: 2, nodes: 0 },
]
</script>

<template>
  <ol class="ladder" :class="{ compact }" aria-label="Deployment ladder">
    <li
      v-for="rung in [...rungs].reverse()"
      :key="rung.lesson"
      :class="{ current: rung.lesson === current, done: current > 0 && rung.lesson < current, later: current > 0 && rung.lesson > current, hidden: rung.lesson > revealed }"
      :style="{ marginLeft: compact ? `${(rung.lesson - 1) * 14}px` : `${(rung.lesson - 1) * 34}px` }"
    >
      <span class="number">{{ rung.lesson }}</span>
      <div class="text">
        <strong>{{ rung.name }}</strong>
        <span v-if="!compact">{{ rung.model }} · {{ rung.shape }}</span>
        <span v-else>{{ rung.model }}</span>
      </div>
      <!-- nodes 0 means the Pods can land on one node or on two, so the GPUs are apart but have no node outline. -->
      <span class="gpus" :title="rung.nodes === 0 ? `${rung.gpus} GPUs on one or two nodes` : `${rung.gpus} GPUs`">
        <i v-for="gpu in rung.gpus" :key="gpu" :class="{ split: rung.nodes === 2 && gpu === 2, apart: rung.nodes === 0 && gpu === 2 }" />
      </span>
    </li>
  </ol>
</template>

<style scoped>
.ladder {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ladder li {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  transition: opacity 0.3s, transform 0.3s;
}

.ladder li.current {
  border-color: var(--accent);
  box-shadow: 0 0 24px -8px var(--accent);
}

.ladder li.later {
  opacity: 0.45;
}

.ladder li.done {
  opacity: 0.7;
}

.ladder li.hidden {
  opacity: 0;
  transform: translateY(10px);
}

.number {
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}

.current .number {
  color: var(--accent);
}

.text {
  display: flex;
  flex: 1;
  flex-direction: column;
  line-height: 1.25;
}

.text strong {
  font-size: 1rem;
}

.text span {
  font-size: 0.75rem;
  color: var(--ink-muted);
}

.gpus {
  display: flex;
  gap: 4px;
}

.gpus i {
  width: 16px;
  height: 22px;
  border-radius: 3px;
  background: var(--req-1);
}

.gpus i.split {
  margin-left: 6px;
  outline: 1px dashed var(--ink-faint);
  outline-offset: 3px;
}

.gpus i.apart {
  margin-left: 6px;
}

.compact li {
  gap: 8px;
  padding: 7px 10px;
}

.compact .number {
  font-size: 1rem;
}

.compact .text strong {
  font-size: 0.82rem;
}

.compact .text span {
  font-size: 0.65rem;
}

.compact .gpus i {
  width: 11px;
  height: 16px;
}
</style>
