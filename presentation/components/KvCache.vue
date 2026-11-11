<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { playbackSpeeds, usePlayback } from '../composables/usePlayback'
import { requestClass } from '../composables/requestClass'
import { kvConfig, kvPoolTokens, kvRequests } from '../simulator/scenarios'
import { createState, isDone, type Request, reservationFor, reservedBlocks, type State, step } from '../simulator/serving'

const blockSize = ref(1)
const blockOptions = [
  { value: 1, label: '1 token' },
  { value: 4, label: '4 tokens' },
]
const speedOptions = playbackSpeeds.map(speed => ({ value: speed.delay, label: speed.label }))

const config = computed(() => kvConfig(blockSize.value))
const poolBlocks = computed(() => config.value.kv!.poolBlocks)

function fresh(): State {
  return createState(config.value, kvRequests)
}

const state = ref<State>(fresh())
const finished = computed(() => isDone(state.value))

function advance(): boolean {
  if (finished.value)
    return false
  state.value = step(state.value)
  return !finished.value
}

const { playing, delay, play, pause } = usePlayback(advance)

function reset() {
  pause()
  state.value = fresh()
}

watch(blockSize, reset)

interface PoolBlock {
  id: number
  owner: string | null
  used: number
}

// Physical blocks: a request fills its blocks in order, so only its last block can be partly used.
const pool = computed<PoolBlock[]>(() => {
  const blocks: PoolBlock[] = Array.from({ length: poolBlocks.value }, (_, id) => ({ id, owner: null, used: 0 }))
  for (const id of state.value.active) {
    const request = state.value.requests[id]
    request.blocks.forEach((blockId, index) => {
      const used = Math.min(blockSize.value, request.processedInputs - index * blockSize.value)
      blocks[blockId] = { id: blockId, owner: id, used }
    })
  }
  return blocks
})

const reserved = computed(() => reservedBlocks(state.value))
const allocated = computed(() => pool.value.filter(block => block.owner !== null).length)
const waste = computed(() => pool.value.reduce((sum, block) => sum + (block.owner === null ? 0 : blockSize.value - block.used), 0))

const reservationBar = computed(() => state.value.active.map((id) => {
  const request = state.value.requests[id]
  return { id, allocated: request.blocks.length, unused: request.reservedBlocks - request.blocks.length }
}))

function phase(request: Request): string {
  if (request.completedAt !== null)
    return 'done'
  if (request.admittedAt === null) {
    const head = state.value.waiting[0]
    if (head === undefined)
      return 'queued'
    if (head !== request.id)
      return `waits behind ${head}`
    const need = reservationFor(config.value, request)
    const free = poolBlocks.value - reserved.value
    if (need <= free && state.value.active.length < config.value.maxSequences)
      return 'starts next step'
    return `waits: needs ${need}, ${free} free`
  }
  if (request.prefilled < request.promptTokens)
    return 'prefill'
  return `decode ${request.emitted}/${request.outputTokens}`
}

const rows = computed(() => state.value.order.map((id) => {
  const request = state.value.requests[id]
  return {
    id,
    request,
    need: reservationFor(config.value, request),
    phase: phase(request),
  }
}))

const lastStep = computed(() => state.value.steps[state.value.steps.length - 1])

const summary = computed(() => {
  const record = lastStep.value
  if (!record)
    return ''
  const parts: string[] = []
  if (record.admitted.length > 0)
    parts.push(`${record.admitted.join(', ')} reserved blocks and started`)
  if (record.completed.length > 0)
    parts.push(`${record.completed.join(', ')} finished and released ${record.completed.length === 1 ? 'its' : 'their'} blocks`)
  const head = state.value.waiting[0]
  if (head) {
    const need = reservationFor(config.value, state.value.requests[head])
    const free = poolBlocks.value - reserved.value
    parts.push(need <= free ? `${head} fits now and starts next step` : `${head} needs ${need} free blocks; ${free} are free`)
  }
  return parts.length > 0 ? `${parts.join('. ')}.` : 'Every running request processed one more input token.'
})
</script>

<template>
  <div class="kv">
    <header>
      <p class="kicker">Simulation C · KV cache <span class="badge simulated">Simulated</span></p>
      <h1>KV Cache Blocks and Reservations</h1>
      <p class="setup">
        A pool of <strong>{{ kvPoolTokens }} token slots</strong> and <strong>4 sequence slots</strong>.
        Before a request starts, it reserves blocks for its whole prompt and output.
      </p>
    </header>

    <div class="config">
      <Segmented v-model="blockSize" label="Block size" :options="blockOptions" />
      <Segmented v-model="delay" label="Speed" :options="speedOptions" />
    </div>

    <div class="main">
      <div class="pool-side">
        <div class="reservation" role="img" :aria-label="`${reserved} of ${poolBlocks} blocks reserved`">
          <div class="bar">
            <template v-for="item in reservationBar" :key="item.id">
              <span class="part allocated" :class="requestClass(item.id)" :style="{ flex: item.allocated }" />
              <span class="part unused" :class="requestClass(item.id)" :style="{ flex: item.unused }" />
            </template>
            <span class="part free" :style="{ flex: poolBlocks - reserved }" />
          </div>
          <p class="bar-caption">
            <span><strong>{{ reserved }}</strong>/{{ poolBlocks }} blocks reserved</span>
            <span><strong>{{ allocated }}</strong> allocated</span>
            <span><strong>{{ poolBlocks - reserved }}</strong> free to reserve</span>
            <span><strong>{{ waste }}</strong> token slots wasted inside blocks</span>
          </p>
        </div>

        <div class="pool" :class="`size-${blockSize}`" role="img" :aria-label="`KV block pool, block size ${blockSize}`">
          <div v-for="block in pool" :key="`${block.id}-${block.owner}`" class="block" :class="block.owner ? requestClass(block.owner) : 'free'">
            <span v-for="slot in blockSize" :key="slot" class="slot" :class="{ used: slot <= block.used, waste: block.owner && slot > block.used }" />
            <span v-if="blockSize > 1" class="block-id">{{ block.id }}</span>
          </div>
        </div>
      </div>

      <table class="requests">
        <thead>
          <tr><th>Req</th><th>Size</th><th>Cached</th><th>Blocks</th><th>State</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" :class="{ waiting: row.phase.startsWith('waits') }">
            <td><span class="dot" :class="requestClass(row.id)" />{{ row.id }}</td>
            <td>{{ row.request.promptTokens }}+{{ row.request.outputTokens }}</td>
            <td>{{ row.request.completedAt === null ? row.request.processedInputs : '—' }}</td>
            <td>{{ row.request.completedAt === null ? `${row.request.blocks.length}/${row.request.admittedAt === null ? row.need : row.request.reservedBlocks}` : '—' }}</td>
            <td class="state">{{ row.phase }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="summary" aria-live="polite">
      <template v-if="!lastStep">Each request reserves <span class="formula">ceil((prompt + output − 1) / {{ blockSize }})</span> blocks before it starts.</template>
      <template v-else>{{ summary }}</template>
    </p>
    <p class="setup">This simulation reserves enough KV space for each request to finish before it starts. vLLM allocates space as needed and may pause requests when space runs out.</p>

    <footer class="controls" @mousedown.prevent>
      <span class="clock">Step {{ state.steps.length }}</span>
      <span class="legend">
        <i class="key used" /> cached token <i class="key waste" /> wasted slot <i class="key unused" /> reserved, not allocated
      </span>
      <button type="button" class="sim-button primary" :disabled="finished || playing" @click="advance">Step</button>
      <button type="button" class="sim-button" :disabled="finished" @click="playing ? pause() : play()">{{ playing ? 'Pause' : 'Play' }}</button>
      <button type="button" class="sim-button" :disabled="state.steps.length === 0" @click="reset">Reset</button>
    </footer>
  </div>
</template>

<style scoped>
.kv {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 10px;
}

header h1 {
  margin: 2px 0 4px;
  font-size: 1.9rem;
}

.setup {
  margin: 0;
  font-size: 0.85rem;
}

.config {
  display: flex;
  justify-content: space-between;
}

.main {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 22px;
  align-items: start;
}

.pool-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar {
  display: flex;
  height: 16px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 5px;
}

.part {
  transition: flex 0.3s ease-out;
}

.part.allocated {
  background: var(--req);
}

.part.unused {
  background: repeating-linear-gradient(-45deg, transparent 0 4px, var(--req) 4px 6px);
  opacity: 0.6;
}

.bar-caption {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 14px;
  margin: 5px 0 0;
  font-size: 0.8rem;
  color: var(--ink-faint);
}

.bar-caption strong {
  font-variant-numeric: tabular-nums;
}

.pool {
  display: grid;
  gap: 6px;
}

.pool.size-4 {
  grid-template-columns: repeat(6, 1fr);
  row-gap: 20px;
}

.pool.size-1 {
  grid-template-columns: repeat(12, 1fr);
  gap: 4px;
}

.block {
  position: relative;
  display: flex;
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 5px;
  animation: pop 0.25s ease-out;
}

.block:not(.free) {
  border-color: var(--req);
}

.slot {
  flex: 1;
  height: 30px;
  border-radius: 2px;
}

.pool.size-1 .slot {
  height: 24px;
}

.slot.used {
  background: var(--req);
}

.slot.waste {
  background: repeating-linear-gradient(-45deg, transparent 0 3px, rgb(var(--tint) / 0.18) 3px 5px);
}

.block-id {
  position: absolute;
  bottom: -14px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.7rem;
  color: var(--ink-faint);
}

.pool.size-4 {
  margin-bottom: 12px;
}

.requests {
  font-size: 0.85rem;
}

.requests th,
.requests td {
  font-size: inherit;
  padding: 5px 6px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.requests tr.waiting td {
  color: var(--req-3);
}

.state {
  white-space: nowrap;
}

.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 5px;
  border-radius: 50%;
  background: var(--req);
}

.summary {
  margin: 0;
  font-size: 0.9rem;
}

.formula {
  font-family: var(--mono);
  font-weight: 700;
}

.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}

.clock {
  min-width: 60px;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  color: var(--ink-muted);
}

.legend {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--ink-faint);
}

.key {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-left: 8px;
  border-radius: 2px;
}

.key.used {
  background: var(--req-1);
}

.key.waste {
  border: 1px solid var(--req-1);
  background: repeating-linear-gradient(-45deg, transparent 0 3px, rgb(var(--tint) / 0.3) 3px 5px);
}

.key.unused {
  background: repeating-linear-gradient(-45deg, transparent 0 3px, var(--req-1) 3px 5px);
  opacity: 0.6;
}

@media (prefers-reduced-motion: reduce) {
  .block { animation: none; }
  .part { transition: none; }
}
</style>
