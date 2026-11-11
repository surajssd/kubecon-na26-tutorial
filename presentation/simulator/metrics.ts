import { isDone, type Request, type State } from './serving'

export interface RequestMetrics {
  id: string
  queueWait: number | null
  ttft: number | null
  tpot: number | null
  e2e: number | null
  outputs: number
}

export interface Stats {
  count: number
  median: number
  max: number
}

export interface RunSummary {
  complete: boolean
  requests: number
  completedRequests: number
  window: { start: number, end: number }
  outputTokens: number
  outputThroughput: number
  requestThroughput: number
  meanRunning: number
  peakRunning: number
  ttft: Stats | null
  tpot: Stats | null
  e2e: Stats | null
}

// TPOT excludes the first token, so it needs at least two outputs.
export function requestMetrics(request: Request): RequestMetrics {
  const first = request.outputTimes[0]
  const last = request.outputTimes[request.outputTimes.length - 1]
  const finished = request.completedAt !== null
  return {
    id: request.id,
    queueWait: request.admittedAt === null ? null : request.admittedAt - request.arrival,
    ttft: first === undefined ? null : first - request.arrival,
    tpot: finished && request.outputTimes.length >= 2 ? (last - first) / (request.outputTimes.length - 1) : null,
    e2e: finished ? request.completedAt! - request.arrival : null,
    outputs: request.emitted,
  }
}

export function stats(values: (number | null)[]): Stats | null {
  const known = values.filter((value): value is number => value !== null).sort((a, b) => a - b)
  if (known.length === 0)
    return null
  const middle = Math.floor(known.length / 2)
  const median = known.length % 2 === 1 ? known[middle] : (known[middle - 1] + known[middle]) / 2
  return { count: known.length, median, max: known[known.length - 1] }
}

// A complete run is measured from the first arrival to the last completion,
// including idle time. An incomplete run is measured up to the current time
// and its rates are provisional.
export function summarize(state: State): RunSummary {
  const all = state.order.map(id => state.requests[id])
  if (all.length === 0)
    throw new Error('A run needs at least one request.')
  const start = Math.min(...all.map(request => request.arrival))
  const complete = isDone(state)
  const end = complete ? Math.max(...all.map(request => request.completedAt!)) : state.time
  const span = end - start
  const outputTokens = all.reduce((sum, request) => sum + request.emitted, 0)
  const busy = state.steps.filter(record => !record.idle && record.end > start)
  const runningTime = busy.reduce((sum, record) => sum + record.running * (record.end - Math.max(record.start, start)), 0)
  const metrics = all.map(requestMetrics)
  return {
    complete,
    requests: all.length,
    completedRequests: state.completed.length,
    window: { start, end },
    outputTokens,
    outputThroughput: span > 0 ? outputTokens / span : 0,
    requestThroughput: span > 0 ? state.completed.length / span : 0,
    meanRunning: span > 0 ? runningTime / span : 0,
    peakRunning: Math.max(0, ...busy.map(record => record.running)),
    ttft: stats(metrics.map(metric => metric.ttft)),
    tpot: stats(metrics.map(metric => metric.tpot)),
    e2e: stats(metrics.map(metric => metric.e2e)),
  }
}
