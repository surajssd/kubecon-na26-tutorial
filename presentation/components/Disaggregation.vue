<script setup lang="ts">
import podIcon from '../assets/icons/pod.svg'
</script>

<template>
  <figure class="disagg" role="img" aria-label="Disaggregated serving: the Dynamo frontend sends the prompt to the prefill worker, NIXL moves the KV cache to the decode worker, and the decode worker streams output tokens back through the frontend">
    <div class="flow">
      <div v-click="1" class="box client">Demo page</div>
      <span v-click="2" class="arrow">⇄</span>
      <div v-click="2" class="box frontend">
        <div class="title"><img :src="podIcon" alt="" class="pod-icon"><strong>Dynamo frontend</strong></div>
        <span>CPU Pod · routes requests</span>
      </div>
      <div class="workers">
        <div v-click="3" class="box worker prefill">
          <div class="title"><img :src="podIcon" alt="" class="pod-icon"><GpuIcon width="20" height="20" /><strong>Prefill worker</strong></div>
          <span>1 GPU · full model</span>
          <span>reads the prompt, builds the KV cache</span>
        </div>
        <div v-click="4" class="transfer">
          <span class="arrow down">⇓</span>
          <p><strong>KV cache via NIXL</strong><br>over TCP</p>
        </div>
        <div v-click="4" class="box worker decode">
          <div class="title"><img :src="podIcon" alt="" class="pod-icon"><GpuIcon width="20" height="20" /><strong>Decode worker</strong></div>
          <span>1 GPU · full model</span>
          <span>generates output tokens</span>
        </div>
      </div>
    </div>
  </figure>
</template>

<style scoped>
.disagg {
  margin: 18px 0 22px;
}

.flow {
  display: grid;
  grid-template-columns: 130px 36px 230px 1fr;
  align-items: center;
  gap: 12px;
}

.box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
}

.box strong {
  font-size: 1.05rem;
}

.title {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pod-icon {
  width: 20px;
  height: 20px;
}

.box span {
  font-size: 1rem;
  color: var(--ink-muted);
}

.client {
  align-items: center;
  font-size: 1rem;
}

.frontend {
  border-color: var(--req-5);
}

.workers {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prefill {
  border-color: var(--req-1);
  box-shadow: inset 4px 0 0 var(--req-1);
}

.decode {
  border-color: var(--req-2);
  box-shadow: inset 4px 0 0 var(--req-2);
}

.transfer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 18px;
}

.transfer p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.3;
  color: var(--ink-muted);
}

.arrow {
  font-size: 1.5rem;
  text-align: center;
  color: var(--accent);
}

</style>
