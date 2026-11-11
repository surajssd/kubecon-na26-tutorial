// A teaching model of one model server. It is not vLLM's scheduler: it admits
// requests in FIFO order, gives every decoding request one input token per
// step, and spends the rest of the token budget on the oldest prefill.

export type Policy = 'static' | 'continuous'

// Duration of one step, in simulated time units:
// fixed + prefill * prompt inputs + decode * decode sequences + context * cached inputs of decode sequences.
export interface Timing {
  fixed: number
  prefillPerToken: number
  decodePerSequence: number
  contextPerToken: number
}

export interface KvConfig {
  blockSize: number
  poolBlocks: number
}

export interface ServingConfig {
  policy: Policy
  maxSequences: number
  tokenBudget: number
  timing: Timing
  kv?: KvConfig
}

export interface RequestSpec {
  id: string
  arrival: number
  promptTokens: number
  outputTokens: number
}

export interface Request extends RequestSpec {
  prefilled: number
  emitted: number
  processedInputs: number
  reservedBlocks: number
  blocks: number[]
  admittedAt: number | null
  outputTimes: number[]
  completedAt: number | null
}

export interface StepRecord {
  index: number
  start: number
  end: number
  idle: boolean
  running: number
  arrived: string[]
  admitted: string[]
  decoded: string[]
  prefill: { requestId: string, tokens: number } | null
  firstTokens: string[]
  completed: string[]
}

export interface State {
  config: ServingConfig
  time: number
  order: string[]
  pending: string[]
  waiting: string[]
  active: string[]
  completed: string[]
  requests: Record<string, Request>
  freeBlocks: number[]
  steps: StepRecord[]
}

function check(condition: boolean, message: string) {
  if (!condition)
    throw new Error(message)
}

function isCount(value: number, minimum: number): boolean {
  return Number.isInteger(value) && value >= minimum
}

export function reservationFor(config: ServingConfig, spec: Pick<RequestSpec, 'promptTokens' | 'outputTokens'>): number {
  if (!config.kv)
    return 0
  return Math.ceil((spec.promptTokens + spec.outputTokens - 1) / config.kv.blockSize)
}

export function createState(config: ServingConfig, requests: RequestSpec[]): State {
  const { timing, kv } = config
  check(isCount(config.maxSequences, 1), 'The sequence limit must be a positive integer.')
  check(isCount(config.tokenBudget, config.maxSequences), 'The token budget must be at least the sequence limit.')
  check(timing.fixed > 0, 'The fixed step cost must be positive.')
  check(timing.prefillPerToken >= 0 && timing.decodePerSequence >= 0 && timing.contextPerToken >= 0, 'Timing coefficients must not be negative.')
  if (kv)
    check(isCount(kv.blockSize, 1) && isCount(kv.poolBlocks, 1), 'Block size and pool size must be positive integers.')
  const empty: State = {
    config,
    time: 0,
    order: [],
    pending: [],
    waiting: [],
    active: [],
    completed: [],
    requests: {},
    freeBlocks: kv ? Array.from({ length: kv.poolBlocks }, (_, index) => index) : [],
    steps: [],
  }
  return requests.reduce(addRequest, empty)
}

// Requests that can never fit are rejected here, so the FIFO queue cannot
// block forever behind them.
export function addRequest(state: State, spec: RequestSpec): State {
  check(!(spec.id in state.requests), `Request ${spec.id} already exists.`)
  check(isCount(spec.promptTokens, 1) && isCount(spec.outputTokens, 1), 'Prompt and output lengths must be positive integers.')
  check(spec.arrival >= state.time, 'A request cannot arrive before the current time.')
  const reservation = reservationFor(state.config, spec)
  if (state.config.kv)
    check(reservation <= state.config.kv.poolBlocks, `Request ${spec.id} needs ${reservation} blocks, but the pool has ${state.config.kv.poolBlocks}.`)
  const request: Request = {
    ...spec,
    prefilled: 0,
    emitted: 0,
    processedInputs: 0,
    reservedBlocks: 0,
    blocks: [],
    admittedAt: null,
    outputTimes: [],
    completedAt: null,
  }
  const order = [...state.order, spec.id]
  const requests = { ...state.requests, [spec.id]: request }
  const pending = [...state.pending, spec.id]
    .sort((a, b) => requests[a].arrival - requests[b].arrival || order.indexOf(a) - order.indexOf(b))
  return { ...state, order, pending, requests }
}

export function isDone(state: State): boolean {
  return state.pending.length === 0 && state.waiting.length === 0 && state.active.length === 0
}

export function reservedBlocks(state: State): number {
  return state.active.reduce((sum, id) => sum + state.requests[id].reservedBlocks, 0)
}

export function step(state: State): State {
  if (isDone(state))
    return state

  const { config } = state
  const start = state.time
  const requests = { ...state.requests }
  const update = (id: string, changes: Partial<Request>) => {
    requests[id] = { ...requests[id], ...changes }
  }

  const arrived = state.pending.filter(id => requests[id].arrival <= start)
  const pending = state.pending.slice(arrived.length)
  const waiting = [...state.waiting, ...arrived]
  const active = [...state.active]

  if (active.length === 0 && waiting.length === 0) {
    const next = requests[pending[0]].arrival
    const idle: StepRecord = { index: state.steps.length, start, end: next, idle: true, running: 0, arrived, admitted: [], decoded: [], prefill: null, firstTokens: [], completed: [] }
    return { ...state, time: next, pending, waiting, steps: [...state.steps, idle] }
  }

  const admitted: string[] = []
  let reserved = reservedBlocks(state)
  const canAdmit = config.policy === 'continuous' || active.length === 0
  while (canAdmit && waiting.length > 0 && active.length < config.maxSequences) {
    const id = waiting[0]
    const need = reservationFor(config, requests[id])
    if (config.kv && reserved + need > config.kv.poolBlocks)
      break
    waiting.shift()
    active.push(id)
    admitted.push(id)
    reserved += need
    update(id, { admittedAt: start, reservedBlocks: need })
  }

  const decoded = active.filter(id => requests[id].prefilled === requests[id].promptTokens)
  const prefillId = active.find(id => requests[id].prefilled < requests[id].promptTokens)
  const budgetLeft = config.tokenBudget - decoded.length
  const prefillTokens = prefillId === undefined ? 0 : Math.min(requests[prefillId].promptTokens - requests[prefillId].prefilled, budgetLeft)
  const decodeContext = decoded.reduce((sum, id) => sum + requests[id].processedInputs, 0)

  const { timing } = config
  const end = start
    + timing.fixed
    + timing.prefillPerToken * prefillTokens
    + timing.decodePerSequence * decoded.length
    + timing.contextPerToken * decodeContext

  for (const id of decoded) {
    const request = requests[id]
    update(id, {
      emitted: request.emitted + 1,
      processedInputs: request.processedInputs + 1,
      outputTimes: [...request.outputTimes, end],
    })
  }

  const firstTokens: string[] = []
  if (prefillId !== undefined && prefillTokens > 0) {
    const request = requests[prefillId]
    const prefilled = request.prefilled + prefillTokens
    const finished = prefilled === request.promptTokens
    update(prefillId, {
      prefilled,
      processedInputs: request.processedInputs + prefillTokens,
      emitted: finished ? 1 : 0,
      outputTimes: finished ? [end] : [],
    })
    if (finished)
      firstTokens.push(prefillId)
  }

  let freeBlocks = [...state.freeBlocks]
  if (config.kv) {
    const { blockSize } = config.kv
    for (const id of active) {
      const request = requests[id]
      const needed = Math.ceil(request.processedInputs / blockSize) - request.blocks.length
      if (needed > 0) {
        update(id, { blocks: [...request.blocks, ...freeBlocks.slice(0, needed)] })
        freeBlocks = freeBlocks.slice(needed)
      }
    }
  }

  const completed = active.filter(id => requests[id].emitted === requests[id].outputTokens)
  for (const id of completed) {
    freeBlocks = [...freeBlocks, ...requests[id].blocks].sort((a, b) => a - b)
    update(id, { completedAt: end, reservedBlocks: 0, blocks: [] })
  }

  const record: StepRecord = {
    index: state.steps.length,
    start,
    end,
    idle: false,
    running: active.length,
    arrived,
    admitted,
    decoded,
    prefill: prefillId !== undefined && prefillTokens > 0 ? { requestId: prefillId, tokens: prefillTokens } : null,
    firstTokens,
    completed,
  }

  return {
    ...state,
    time: end,
    pending,
    waiting,
    active: active.filter(id => !completed.includes(id)),
    completed: [...state.completed, ...completed],
    requests,
    freeBlocks,
    steps: [...state.steps, record],
  }
}

export function runToEnd(state: State, maxSteps = 10_000): State {
  let current = state
  for (let count = 0; !isDone(current); count++) {
    check(count < maxSteps, `The scenario did not finish within ${maxSteps} steps.`)
    current = step(current)
  }
  return current
}
