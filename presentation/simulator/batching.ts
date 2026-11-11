export type Policy = 'static' | 'continuous'

export interface RequestSpec {
  id: string
  outputTokens: number
}

export interface Scenario {
  capacity: number
  requests: RequestSpec[]
}

interface Slot {
  requestId: string
  finished: boolean
}

// A held cell is a slot whose request already finished but which static
// batching cannot refill until every request in the cohort finishes.
export type Cell =
  | { kind: 'token', requestId: string, token: number, last: boolean }
  | { kind: 'held', requestId: string }
  | { kind: 'empty' }

export type Event =
  | { type: 'admit', requestId: string, slot: number }
  | { type: 'finish', requestId: string, slot: number }

export interface State {
  policy: Policy
  iteration: number
  targets: Record<string, number>
  emitted: Record<string, number>
  waiting: string[]
  slots: (Slot | null)[]
  columns: Cell[][]
}

export function initialState(policy: Policy, scenario: Scenario): State {
  if (!Number.isInteger(scenario.capacity) || scenario.capacity < 1)
    throw new Error(`Capacity must be a positive integer, got ${scenario.capacity}.`)
  const empty: State = {
    policy,
    iteration: 0,
    targets: {},
    emitted: {},
    waiting: [],
    slots: Array.from({ length: scenario.capacity }, () => null),
    columns: [],
  }
  return scenario.requests.reduce(addRequest, empty)
}

// A request added between steps joins the queue at the current boundary.
export function addRequest(state: State, request: RequestSpec): State {
  if (!Number.isInteger(request.outputTokens) || request.outputTokens < 1)
    throw new Error(`Output length must be a positive integer, got ${request.outputTokens}.`)
  if (request.id in state.targets)
    throw new Error(`Request ${request.id} already exists.`)
  return {
    ...state,
    targets: { ...state.targets, [request.id]: request.outputTokens },
    emitted: { ...state.emitted, [request.id]: 0 },
    waiting: [...state.waiting, request.id],
  }
}

export function isDone(state: State): boolean {
  return state.waiting.length === 0 && state.slots.every(slot => slot === null)
}

export function step(state: State): { state: State, events: Event[] } {
  if (isDone(state))
    return { state, events: [] }

  const iteration = state.iteration + 1
  const waiting = [...state.waiting]
  const slots = [...state.slots]
  const emitted = { ...state.emitted }
  const events: Event[] = []

  const canAdmit = state.policy === 'continuous' || slots.every(slot => slot === null)
  for (let index = 0; index < slots.length && canAdmit; index++) {
    const requestId = waiting[0]
    if (slots[index] !== null || requestId === undefined)
      continue
    waiting.shift()
    slots[index] = { requestId, finished: false }
    events.push({ type: 'admit', requestId, slot: index })
  }

  const column: Cell[] = []
  for (let index = 0; index < slots.length; index++) {
    const slot = slots[index]
    if (slot === null) {
      column.push({ kind: 'empty' })
      continue
    }
    if (slot.finished) {
      column.push({ kind: 'held', requestId: slot.requestId })
      continue
    }
    const token = emitted[slot.requestId] + 1
    const last = token === state.targets[slot.requestId]
    emitted[slot.requestId] = token
    column.push({ kind: 'token', requestId: slot.requestId, token, last })
    if (last) {
      slots[index] = { ...slot, finished: true }
      events.push({ type: 'finish', requestId: slot.requestId, slot: index })
    }
  }

  const cohortDone = slots.every(slot => slot === null || slot.finished)
  for (let index = 0; index < slots.length; index++) {
    if (slots[index]?.finished && (state.policy === 'continuous' || cohortDone))
      slots[index] = null
  }

  return {
    state: { ...state, iteration, waiting, slots, emitted, columns: [...state.columns, column] },
    events,
  }
}

// A policy with no work still advances with the shared clock, so its idle
// steps stay aligned with the other policy.
export function idle(state: State): State {
  const column: Cell[] = state.slots.map(() => ({ kind: 'empty' }))
  return { ...state, iteration: state.iteration + 1, columns: [...state.columns, column] }
}

export function finishedAt(state: State): number {
  let last = 0
  state.columns.forEach((column, index) => {
    if (column.some(cell => cell.kind === 'token'))
      last = index + 1
  })
  return last
}

export function runToEnd(state: State): State {
  let current = state
  while (!isDone(current))
    current = step(current).state
  return current
}
