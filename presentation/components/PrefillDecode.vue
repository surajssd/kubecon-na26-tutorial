<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { playbackSpeeds, usePlayback } from '../composables/usePlayback'
import { requestClass } from '../composables/requestClass'
import { requestMetrics } from '../simulator/metrics'
import { phaseConfig, phasePresets, teachingTiming } from '../simulator/scenarios'
import { createState, isDone, runToEnd, type State, step } from '../simulator/serving'

const props = withDefaults(defineProps<{ preset?: string }>(), { preset: 'one' })

const preset = computed(() => phasePresets.find(item => item.id === props.preset)!)
const budget = ref(preset.value.budgets[0].tokenBudget)
const budgetOptions = computed(() => preset.value.budgets.map(item => ({ value: item.tokenBudget, label: item.label })))
const speedOptions = playbackSpeeds.map(speed => ({ value: speed.delay, label: speed.label }))

function fresh(): State {
  return createState(phaseConfig(budget.value), preset.value.requests)
}

const state = ref<State>(fresh())
const finished = computed(() => isDone(state.value))

// One time scale for every budget option, so switching budgets keeps bars comparable.
const horizon = computed(() => Math.max(...preset.value.budgets.map(item =>
  runToEnd(createState(phaseConfig(item.tokenBudget), preset.value.requests)).time)))
const tickSize = computed(() => horizon.value <= 12 ? 1 : horizon.value <= 30 ? 2 : 5)
const ticks = computed(() => Array.from({ length: Math.floor(horizon.value / tickSize.value) + 1 }, (_, index) => index * tickSize.value))

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

watch(budget, reset)

const x = (time: number) => `${(time / horizon.value) * 100}%`
const w = (from: number, to: number) => `${((to - from) / horizon.value) * 100}%`
const format = (value: number | null) => value === null ? '—' : value.toFixed(1)

interface Segment {
  key: string
  kind: 'wait' | 'prefill' | 'decode'
  start: number
  end: number
  label: string
}

function segments(id: string): Segment[] {
  const request = state.value.requests[id]
  const result: Segment[] = []
  if (request.arrival <= state.value.time) {
    const admitted = request.admittedAt ?? state.value.time
    if (admitted > request.arrival)
      result.push({ key: 'wait', kind: 'wait', start: request.arrival, end: admitted, label: '' })
  }
  for (const record of state.value.steps) {
    if (record.prefill?.requestId === id)
      result.push({ key: `p${record.index}`, kind: 'prefill', start: record.start, end: record.end, label: `${record.prefill.tokens}` })
    else if (record.decoded.includes(id))
      result.push({ key: `d${record.index}`, kind: 'decode', start: record.start, end: record.end, label: '' })
  }
  return result
}

const rows = computed(() => state.value.order.map((id) => {
  const request = state.value.requests[id]
  return { id, request, segments: segments(id), metrics: requestMetrics(request) }
}))

const lastStep = computed(() => state.value.steps[state.value.steps.length - 1])

const words = computed(() => preset.value.words)
const wordRequest = computed(() => state.value.requests[state.value.order[0]])
const freshPrompt = computed(() => {
  const prefill = lastStep.value?.prefill
  return prefill?.requestId === wordRequest.value.id ? prefill.tokens : 0
})
const freshOutput = computed(() => {
  const record = lastStep.value
  const id = wordRequest.value.id
  return record !== undefined && (record.decoded.includes(id) || record.firstTokens.includes(id))
})
const display = (word: string) => word === '\n' ? '\\n' : word.trim()

interface BudgetCell { kind: 'decode' | 'prefill' | 'unused', requestId?: string }

const budgetCells = computed<BudgetCell[]>(() => {
  const record = lastStep.value
  const cells: BudgetCell[] = []
  if (record && !record.idle) {
    for (const id of record.decoded)
      cells.push({ kind: 'decode', requestId: id })
    for (let index = 0; index < (record.prefill?.tokens ?? 0); index++)
      cells.push({ kind: 'prefill', requestId: record.prefill!.requestId })
  }
  while (cells.length < budget.value)
    cells.push({ kind: 'unused' })
  return cells
})

const stepSummary = computed(() => {
  const record = lastStep.value
  if (!record)
    return 'Press Step to run the first step.'
  if (record.idle)
    return `Idle from ${record.start.toFixed(1)} to ${record.end.toFixed(1)}: nothing to run until the next arrival.`
  const parts: string[] = []
  if (record.decoded.length > 0)
    parts.push(`decode ${record.decoded.join(', ')}`)
  if (record.prefill)
    parts.push(`prefill ${record.prefill.tokens} prompt tokens of ${record.prefill.requestId}`)
  const t = teachingTiming
  const duration = `${t.fixed} + ${t.prefillPerToken} × ${record.prefill?.tokens ?? 0} + ${t.decodePerSequence} × ${record.decoded.length} = ${(record.end - record.start).toFixed(1)}`
  return `Step ${record.index + 1}: ${parts.join(', ')}. Duration ${duration}.`
})
</script>

<template>
  <div class="phases">
    <header>
      <p class="kicker">
        Simulation B · prefill and decode <span class="badge simulated">Simulated</span>
        <span v-if="preset.id === 'busy'" class="badge scope">One GPU · no KV transfer</span>
      </p>
      <h1>{{ preset.id === 'busy' ? 'Long Prefills Can Delay Decode' : 'Prefill, Then One Token per Step' }}</h1>
      <p v-if="preset.id === 'busy'" class="setup">
        One GPU runs prefill and decode for all requests, so a long prompt's prefill shares each step with the running decodes.
        Every step has a <strong>token budget</strong>; prompts can run whole or in chunks.
      </p>
      <p v-else class="setup">
        Prefill reads the prompt and emits the first token. Each decode step reads the last token and emits the next.
        Every step has a <strong>token budget</strong>; prompts can run whole or in chunks.
      </p>
    </header>

    <div class="config">
      <div class="config-right">
        <Segmented v-model="budget" label="Prefill" :options="budgetOptions" />
        <Segmented v-model="delay" label="Speed" :options="speedOptions" />
      </div>
    </div>

    <div class="main">
      <div class="timeline">
        <div class="axis">
          <span v-for="tick in ticks" :key="tick" :style="{ left: x(tick) }">{{ tick }}</span>
        </div>
        <div v-for="row in rows" :key="row.id" class="row" :class="requestClass(row.id)">
          <div class="row-label">
            <strong>{{ row.id }}</strong>
            <span>{{ row.request.promptTokens }} in · {{ row.request.outputTokens }} out</span>
          </div>
          <div class="track">
            <span class="arrival" :style="{ left: x(row.request.arrival) }" :title="`arrives at ${row.request.arrival}`" />
            <div
              v-for="segment in row.segments"
              :key="segment.key"
              class="segment"
              :class="segment.kind"
              :style="{ left: x(segment.start), width: w(segment.start, segment.end) }"
            >
              {{ segment.label }}
            </div>
            <span
              v-for="(time, index) in row.request.outputTimes"
              :key="index"
              class="token"
              :class="{ first: index === 0 }"
              :style="{ left: x(time) }"
            />
            <div
              v-if="row.metrics.ttft !== null"
              class="ttft"
              :style="{ left: x(row.request.arrival), width: w(row.request.arrival, row.request.outputTimes[0]) }"
            >
              <span>TTFT {{ format(row.metrics.ttft) }}</span>
            </div>
          </div>
        </div>
        <div class="now" :style="{ left: `calc(96px + (100% - 96px) * ${state.time / horizon})` }" />
        <p class="axis-caption">Simulated time units</p>
      </div>

      <table class="metrics">
        <thead>
          <tr><th>Req</th><th>Wait</th><th>TTFT</th><th>TPOT</th><th>E2E</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td><span class="dot" :class="requestClass(row.id)" />{{ row.id }}</td>
            <td>{{ format(row.metrics.queueWait) }}</td>
            <td>{{ format(row.metrics.ttft) }}</td>
            <td>{{ row.request.completedAt !== null && row.metrics.tpot === null ? 'N/A' : format(row.metrics.tpot) }}</td>
            <td>{{ format(row.metrics.e2e) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="words" class="words" :class="requestClass(wordRequest.id)">
      <div class="word-row">
        <span class="word-label">Prompt</span>
        <span
          v-for="(word, index) in words.prompt"
          :key="index"
          class="word"
          :class="{
            read: index < wordRequest.prefilled,
            fresh: index >= wordRequest.prefilled - freshPrompt && index < wordRequest.prefilled,
            special: word.startsWith('<|'),
          }"
        >{{ display(word) }}</span>
      </div>
      <div class="word-row">
        <span class="word-label">Output</span>
        <span
          v-for="(word, index) in words.output"
          :key="index"
          class="word output"
          :class="{ shown: index < wordRequest.emitted, fresh: freshOutput && index === wordRequest.emitted - 1 }"
        >{{ display(word) }}</span>
      </div>
    </div>

    <div class="budget">
      <div class="budget-cells" role="img" :aria-label="`Token budget of ${budget} for the last step`">
        <span v-for="(cell, index) in budgetCells" :key="index" class="budget-cell" :class="[cell.kind, cell.requestId ? requestClass(cell.requestId) : '']" />
      </div>
      <p class="step-summary" aria-live="polite">{{ stepSummary }}</p>
    </div>

    <footer class="controls" @mousedown.prevent>
      <span class="clock">t = {{ state.time.toFixed(1) }}</span>
      <span class="legend"><i class="key prefill" /> prefill <i class="key decode" /> decode <i class="key output" /> output token</span>
      <button type="button" class="sim-button primary" :disabled="finished || playing" @click="advance">Step</button>
      <button type="button" class="sim-button" :disabled="finished" @click="playing ? pause() : play()">{{ playing ? 'Pause' : 'Play' }}</button>
      <button type="button" class="sim-button" :disabled="state.steps.length === 0" @click="reset">Reset</button>
    </footer>
  </div>
</template>

<style scoped>
.phases {
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
  align-items: center;
  justify-content: flex-end;
}

.badge.scope {
  color: var(--ink-muted);
  border: 1px solid var(--line);
}

.config-right {
  display: flex;
  gap: 14px;
}

.main {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  align-items: start;
}

.timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.axis {
  position: relative;
  height: 16px;
  margin-left: 96px;
  font-size: 0.8rem;
  color: var(--ink-faint);
  border-bottom: 1px solid var(--line);
}

.axis span {
  position: absolute;
  transform: translateX(-50%);
}

.axis-caption {
  margin: 0 0 0 96px;
  font-size: 0.8rem;
  color: var(--ink-faint);
}

.row {
  display: grid;
  grid-template-columns: 96px 1fr;
  align-items: center;
}

.row-label {
  display: flex;
  flex-direction: column;
  font-size: 0.8rem;
  line-height: 1.2;
  color: var(--ink-faint);
}

.row-label strong {
  font-size: 0.95rem;
  color: var(--req);
}

.track {
  position: relative;
  height: 50px;
  border-radius: 6px;
  background: rgb(var(--tint) / 0.03);
}

.arrival {
  position: absolute;
  top: 6px;
  bottom: 6px;
  width: 2px;
  margin-left: -1px;
  background: var(--req);
  opacity: 0.6;
}

.segment {
  position: absolute;
  top: 19px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--ink-inverse);
  animation: grow 0.3s ease-out;
  transform-origin: left;
}

.segment.prefill {
  background: var(--req);
}

.segment.decode {
  border: 1px solid var(--req);
  background: rgb(var(--tint) / 0.04);
}

.segment.wait {
  border: 1px dashed var(--ink-faint);
  color: var(--ink-faint);
  font-weight: 500;
}

.token {
  position: absolute;
  top: 26px;
  width: 10px;
  height: 10px;
  margin-left: -5px;
  border: 2px solid var(--ink-inverse);
  border-radius: 50%;
  background: var(--ink);
  animation: pop 0.3s ease-out;
}

.token.first {
  width: 14px;
  height: 14px;
  top: 24px;
  margin-left: -7px;
  background: var(--req);
  border-color: var(--ink);
}

.ttft {
  position: absolute;
  top: 2px;
  height: 11px;
  border: 1px solid var(--ink-muted);
  border-bottom: none;
  border-radius: 3px 3px 0 0;
}

.ttft span {
  position: absolute;
  top: -3px;
  left: 4px;
  padding: 0 4px;
  font-size: 0.75rem;
  line-height: 1;
  white-space: nowrap;
  color: var(--ink);
  background: var(--ink-inverse);
}

.now {
  position: absolute;
  top: 16px;
  bottom: 18px;
  width: 2px;
  background: var(--accent);
  box-shadow: 0 0 10px var(--accent);
  transition: left 0.3s ease-out;
}

.metrics {
  font-size: 0.85rem;
}

.metrics th,
.metrics td {
  font-size: inherit;
  padding: 5px 6px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.metrics th:first-child,
.metrics td:first-child {
  text-align: left;
}

.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 5px;
  border-radius: 50%;
  background: var(--req);
}

.words {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.word-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.word-label {
  width: 92px;
  font-size: 0.8rem;
  color: var(--ink-faint);
}

.word {
  padding: 2px 6px;
  border: 1px dashed var(--line);
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 0.8rem;
  white-space: pre;
  color: var(--ink-faint);
  transition: background-color 0.3s, border-color 0.3s, color 0.3s;
}

.word.read {
  border-color: transparent;
  color: var(--ink-inverse);
  background: var(--req);
}

.word.special.read {
  opacity: 0.65;
}

.word.output {
  color: transparent;
}

.word.output.shown {
  border-color: transparent;
  color: var(--ink-inverse);
  background: var(--ink);
}

.word.fresh {
  box-shadow: 0 0 0 2px var(--accent);
  animation: pop 0.3s ease-out;
}

.budget {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.budget-cells {
  display: grid;
  grid-template-columns: repeat(20, 9px);
  gap: 2px;
  flex-shrink: 0;
}

.budget-cell {
  width: 9px;
  height: 9px;
  border-radius: 2px;
}

.budget-cell.unused {
  border: 1px solid var(--line);
}

.budget-cell.prefill {
  background: var(--req);
}

.budget-cell.decode {
  background: var(--ink);
  box-shadow: inset 0 0 0 2px var(--req);
}

.step-summary {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.35;
}

.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}

.clock {
  min-width: 70px;
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
  width: 14px;
  height: 10px;
  margin-left: 8px;
  border-radius: 2px;
}

.key.prefill {
  background: var(--req-1);
}

.key.decode {
  border: 1px solid var(--req-1);
}

.key.output {
  width: 10px;
  border-radius: 50%;
  background: var(--ink);
}

@keyframes grow {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}

@media (prefers-reduced-motion: reduce) {
  .segment, .token, .word { animation: none; }
  .now { transition: none; }
}
</style>
