import { describe, expect, test } from 'bun:test'
import { addRequest, type Cell, finishedAt, idle, initialState, type Policy, runToEnd, step } from './batching'
import { batchingPresets, principal } from './scenarios'

function render(cell: Cell): string {
  if (cell.kind === 'token')
    return `${cell.requestId}.${cell.token}${cell.last ? '!' : ''}`
  return cell.kind === 'held' ? `held:${cell.requestId}` : '-'
}

function trace(policy: Policy): string[] {
  return runToEnd(initialState(policy, principal)).columns.map(column => column.map(render).join(' '))
}

describe('principal fixture: capacity 2, output lengths [2, 5, 2]', () => {
  test('static batching holds r1 slot until r2 finishes, then runs r3', () => {
    expect(trace('static')).toEqual([
      'r1.1 r2.1',
      'r1.2! r2.2',
      'held:r1 r2.3',
      'held:r1 r2.4',
      'held:r1 r2.5!',
      'r3.1 -',
      'r3.2! -',
    ])
  })

  test('continuous batching gives r1 slot to r3 at the next step', () => {
    expect(trace('continuous')).toEqual([
      'r1.1 r2.1',
      'r1.2! r2.2',
      'r3.1 r2.3',
      'r3.2! r2.4',
      '- r2.5!',
    ])
  })
})

describe('other presets and added requests', () => {
  const steps = (policy: Policy, id: string) =>
    runToEnd(initialState(policy, batchingPresets.find(preset => preset.id === id)!.scenario)).iteration

  test('one long request leaves a static slot idle for seven steps', () => {
    expect(steps('static', 'long')).toBe(10)
    expect(steps('continuous', 'long')).toBe(8)
  })

  test('equal lengths give both policies the same number of steps', () => {
    expect(steps('static', 'equal')).toBe(6)
    expect(steps('continuous', 'equal')).toBe(6)
  })

  test('a request added after step 2 joins the queue at that boundary', () => {
    const afterTwo = step(step(initialState('continuous', principal)).state).state
    const done = runToEnd(addRequest(afterTwo, { id: 'r4', outputTokens: 1 }))
    expect(done.columns.map(column => column.map(render).join(' '))).toEqual([
      'r1.1 r2.1',
      'r1.2! r2.2',
      'r3.1 r2.3',
      'r3.2! r2.4',
      'r4.1! r2.5!',
    ])
  })

  test('rejects duplicate ids and empty requests', () => {
    const state = initialState('static', principal)
    expect(() => addRequest(state, { id: 'r1', outputTokens: 1 })).toThrow('already exists')
    expect(() => addRequest(state, { id: 'r9', outputTokens: 0 })).toThrow('positive integer')
  })
})

describe('shared clock', () => {
  test('an idle step adds an empty column and keeps the finish step', () => {
    const done = runToEnd(initialState('continuous', principal))
    const waited = idle(done)
    expect(waited.iteration).toBe(6)
    expect(waited.columns[5].map(render)).toEqual(['-', '-'])
    expect(finishedAt(waited)).toBe(5)
  })
})
