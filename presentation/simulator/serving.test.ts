import { describe, expect, test } from 'bun:test'
import { requestMetrics, summarize } from './metrics'
import { addRequest, createState, type RequestSpec, reservedBlocks, runToEnd, type ServingConfig, type State, step, type StepRecord } from './serving'

const flat = { fixed: 1, prefillPerToken: 0, decodePerSequence: 0, contextPerToken: 0 }

function render(record: StepRecord): string {
  if (record.idle)
    return `${record.start}-${record.end} idle`
  const prefill = record.prefill ? ` prefill ${record.prefill.requestId}x${record.prefill.tokens}` : ''
  const decode = record.decoded.length > 0 ? ` decode ${record.decoded.join(',')}` : ''
  return `${record.start}-${record.end}${decode}${prefill}`
}

function steps(state: State, count: number): State {
  let current = state
  for (let index = 0; index < count; index++)
    current = step(current)
  return current
}

describe('one request', () => {
  const config: ServingConfig = {
    policy: 'continuous',
    maxSequences: 2,
    tokenBudget: 4,
    timing: { fixed: 1, prefillPerToken: 0.25, decodePerSequence: 0.5, contextPerToken: 0 },
  }
  const spec: RequestSpec = { id: 'r1', arrival: 0, promptTokens: 6, outputTokens: 3 }

  test('prefills in budget-sized chunks, then decodes one token per step', () => {
    const done = runToEnd(createState(config, [spec]))
    expect(done.steps.map(render)).toEqual([
      '0-2 prefill r1x4',
      '2-3.5 prefill r1x2',
      '3.5-5 decode r1',
      '5-6.5 decode r1',
    ])
    expect(done.requests.r1.outputTimes).toEqual([3.5, 5, 6.5])
    expect(done.requests.r1.processedInputs).toBe(6 + 3 - 1)
    expect(requestMetrics(done.requests.r1)).toEqual({ id: 'r1', queueWait: 0, ttft: 3.5, tpot: 1.5, e2e: 6.5, outputs: 3 })
  })

  test('decode steps cost more as the cached context grows', () => {
    const timing = { ...config.timing, contextPerToken: 0.1 }
    const done = runToEnd(createState({ ...config, timing }, [spec]))
    expect(done.steps.map(record => record.end)).toEqual([2, 3.5, 5.6, 7.8])
  })
})

describe('timed arrivals', () => {
  const config: ServingConfig = {
    policy: 'continuous',
    maxSequences: 2,
    tokenBudget: 4,
    timing: { fixed: 1, prefillPerToken: 0.5, decodePerSequence: 0.5, contextPerToken: 0 },
  }
  const specs: RequestSpec[] = [
    { id: 'r1', arrival: 0, promptTokens: 2, outputTokens: 2 },
    { id: 'r2', arrival: 1, promptTokens: 2, outputTokens: 2 },
    { id: 'r3', arrival: 20, promptTokens: 1, outputTokens: 1 },
  ]

  test('a mid-step arrival waits for the next boundary and an idle gap skips ahead', () => {
    const done = runToEnd(createState(config, specs))
    expect(done.steps.map(render)).toEqual([
      '0-2 prefill r1x2',
      '2-4.5 decode r1 prefill r2x2',
      '4.5-6 decode r2',
      '6-20 idle',
      '20-21.5 prefill r3x1',
    ])
    expect(requestMetrics(done.requests.r2)).toEqual({ id: 'r2', queueWait: 1, ttft: 3.5, tpot: 1.5, e2e: 5, outputs: 2 })
    expect(requestMetrics(done.requests.r3).tpot).toBeNull()
  })

  test('throughput uses first arrival to last completion, including idle time', () => {
    const summary = summarize(runToEnd(createState(config, specs)))
    expect(summary.complete).toBe(true)
    expect(summary.window).toEqual({ start: 0, end: 21.5 })
    expect(summary.outputThroughput).toBeCloseTo(5 / 21.5)
    expect(summary.requestThroughput).toBeCloseTo(3 / 21.5)
    expect(summary.meanRunning).toBeCloseTo((2 + 5 + 1.5 + 1.5) / 21.5)
    expect(summary.peakRunning).toBe(2)
    expect(summary.tpot?.count).toBe(2)
  })

  test('an unfinished run reports a provisional window up to the current time', () => {
    const summary = summarize(steps(createState(config, specs), 2))
    expect(summary.complete).toBe(false)
    expect(summary.window).toEqual({ start: 0, end: 4.5 })
    expect(summary.completedRequests).toBe(1)
  })
})

describe('static and continuous admission', () => {
  const specs: RequestSpec[] = [
    { id: 'r1', arrival: 0, promptTokens: 1, outputTokens: 1 },
    { id: 'r2', arrival: 0, promptTokens: 1, outputTokens: 3 },
    { id: 'r3', arrival: 0, promptTokens: 1, outputTokens: 1 },
  ]
  const run = (policy: 'static' | 'continuous') =>
    runToEnd(createState({ policy, maxSequences: 2, tokenBudget: 4, timing: flat }, specs))

  test('continuous admission gives r1 slot to r3 one step after r1 finishes', () => {
    expect(run('continuous').steps.map(render)).toEqual([
      '0-1 prefill r1x1',
      '1-2 prefill r2x1',
      '2-3 decode r2 prefill r3x1',
      '3-4 decode r2',
    ])
  })

  test('static admission holds r3 until the whole first batch finishes', () => {
    const done = run('static')
    expect(done.steps.map(render)).toEqual([
      '0-1 prefill r1x1',
      '1-2 prefill r2x1',
      '2-3 decode r2',
      '3-4 decode r2',
      '4-5 prefill r3x1',
    ])
    expect(requestMetrics(done.requests.r3).ttft).toBe(5)
  })
})

describe('KV blocks and reservations', () => {
  const config: ServingConfig = {
    policy: 'continuous',
    maxSequences: 4,
    tokenBudget: 8,
    timing: flat,
    kv: { blockSize: 2, poolBlocks: 4 },
  }
  const specs: RequestSpec[] = [
    { id: 'r1', arrival: 0, promptTokens: 3, outputTokens: 2 },
    { id: 'r2', arrival: 0, promptTokens: 3, outputTokens: 4 },
    { id: 'r3', arrival: 0, promptTokens: 1, outputTokens: 1 },
  ]
  const initial = createState(config, specs)

  test('a request waits until its whole reservation fits, and FIFO holds later requests behind it', () => {
    const done = runToEnd(initial)
    expect(done.steps.map(record => record.admitted.join(','))).toEqual(['r1', '', 'r2,r3', '', '', ''])
    expect(requestMetrics(done.requests.r3).queueWait).toBe(2)
  })

  test('blocks are allocated as inputs are processed and reused lowest id first', () => {
    const afterThree = steps(initial, 3)
    expect(afterThree.requests.r2.reservedBlocks).toBe(3)
    expect(afterThree.requests.r2.blocks).toEqual([0, 1])
    expect(afterThree.freeBlocks).toEqual([2, 3])
    const afterFive = steps(initial, 5)
    expect(afterFive.requests.r2.processedInputs).toBe(5)
    expect(afterFive.requests.r2.blocks).toEqual([0, 1, 2])
  })

  test('allocation never exceeds reservation, and reservations never exceed the pool', () => {
    let state = initial
    while (state.active.length > 0 || state.pending.length > 0 || state.waiting.length > 0) {
      state = step(state)
      for (const id of state.active)
        expect(state.requests[id].blocks.length).toBeLessThanOrEqual(state.requests[id].reservedBlocks)
      expect(reservedBlocks(state)).toBeLessThanOrEqual(4)
    }
    expect(state.freeBlocks).toEqual([0, 1, 2, 3])
  })

  test('a request that can never fit is rejected before it joins the queue', () => {
    expect(() => addRequest(initial, { id: 'big', arrival: 0, promptTokens: 8, outputTokens: 4 })).toThrow('needs 6 blocks')
  })
})

describe('command validation', () => {
  const base: ServingConfig = { policy: 'continuous', maxSequences: 2, tokenBudget: 2, timing: flat }

  test('rejects a token budget below the sequence limit', () => {
    expect(() => createState({ ...base, tokenBudget: 1 }, [])).toThrow('token budget')
  })

  test('rejects a zero fixed cost', () => {
    expect(() => createState({ ...base, timing: { ...flat, fixed: 0 } }, [])).toThrow('fixed step cost')
  })

  test('rejects duplicate ids and arrivals in the past', () => {
    const later = step(createState(base, [{ id: 'r1', arrival: 0, promptTokens: 1, outputTokens: 2 }]))
    expect(() => addRequest(later, { id: 'r1', arrival: 1, promptTokens: 1, outputTokens: 1 })).toThrow('already exists')
    expect(() => addRequest(later, { id: 'r2', arrival: 0, promptTokens: 1, outputTokens: 1 })).toThrow('before the current time')
  })
})
