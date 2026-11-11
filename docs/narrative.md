# Teaching sequence

The presentation complements [lessons 01-04](../tutorial/README.md). Begin deployment with one GPU, then teach tensor parallelism (TP), pipeline parallelism (PP) with LeaderWorkerSet, and disaggregated prefill/decode. CPU deployment and a dedicated CPU baseline chapter are excluded.

The chapters below describe the presentation in `presentation/slides/`. The deck needs a timed rehearsal by both presenters. [Architecture](architecture.md) defines the behavior and limits of the simulations, including the key-value (KV) cache model. Planner holds the implementation backlog.

## Proposed 80-minute agenda

This allocation needs review by both presenters and a timed rehearsal. It includes attendee work, loading, traffic, and explicit cleanup between lessons.

Attendees apply each manifest before the matching explanation, so Pod loading overlaps with teaching. The 32-attendee scale test measured Pod readiness at about 105 seconds for lesson 01, 217 for lesson 02, 280 for lesson 03, and 167 for lesson 04, with mixed cache state. These times are planning inputs, not guarantees.

| Minutes | Segment | Projector and attendee work |
| --- | --- | --- |
| 0-5 | Intro | Live hook, workspace sign-in, caching, batching, GPU placement, the deployment ladder, and workspace orientation |
| 5-6 | Lesson 01 deployment | [Lesson 01](../tutorial/01-vllm/README.md) steps 1 and 2: apply the manifest and follow the logs |
| 6-12 | One model on one GPU | While Qwen loads: what vLLM is and its three parts, inference basics, GPU memory, annotated startup logs, request anatomy, and prefill/decode |
| 12-20 | Lesson 01 hands-on | Steps 3 and 4: API request, streaming demo, and traffic at concurrency 1 and 4 with the Grafana overview |
| 20-21 | Lesson 01 debrief | Concurrency 1 compared with 4, and why the next model does not fit on one GPU |
| 21-23 | Transition | Lesson 01 cleanup, then [lesson 02](../tutorial/02-tensor-parallel/README.md) steps 1 and 2 |
| 23-29 | Batching, memory, and tensor parallelism | While Muse Glimmer loads: Simulations A and C, why two GPUs, and TP within a node |
| 29-36 | Lesson 02 hands-on | Steps 3 to 5 |
| 36-37 | Lesson 02 debrief | Why lesson 02's Pod needed two GPUs on one node |
| 37-39 | Transition | Lesson 02 cleanup, then [lesson 03](../tutorial/03-pipeline-parallel/README.md) steps 1 and 2 |
| 39-44 | Pipeline parallelism and hardware | While the LeaderWorkerSet (LWS) group loads: LWS, PP, and networks between nodes |
| 44-50 | Lesson 03 hands-on | Steps 3 to 5 |
| 50-51 | Lesson 03 debrief | Every request passed through both pipeline stages |
| 51-53 | Transition | Lesson 03 cleanup, then [lesson 04](../tutorial/04-prefill-disaggregation/README.md) steps 1 and 2 |
| 53-57 | Disaggregated prefill/decode | While Dynamo loads: the phase split, what Dynamo is and how one request flows through it, and the KV transfer path |
| 57-64 | Lesson 04 hands-on | Steps 3 to 6 |
| 64-72 | Latency and throughput | Lesson 04 cleanup and debrief, Simulation D, and interpretation of live metrics |
| 72-80 | Recap and questions | Return to the deployment ladder, observed evidence, and capacity guidance |

The agenda has no spare time. If the session overruns, skip the lesson 02 and lesson 03 traffic runs first. Lesson 01 carries the concurrency comparison, and lesson 04 carries the worker split.

The deck combines demonstrations with operational guidance. Simulations A-D are available, so the next step is a timed rehearsal of this full agenda.

Keep lesson 02's core explanation under five minutes and leave one minute for questions or loading delays. Show the uneven-length batching preset and the KV simulation with 1-token blocks. The equal-length comparison, added requests, and block fragmentation are optional. The Gemma cache observation belongs in lesson 04, alongside its worker configuration.

## Chapter teaching contract

| Chapter | Learning objective | Evidence and limits |
| --- | --- | --- |
| Intro | State what attendees will see for themselves | The labs demonstrate caching, batching, and GPU placement. Queue depth and latency are operational guidance for capacity decisions. The tutorial does not demonstrate autoscaling. |
| Request anatomy | Distinguish prompt processing from output generation | Simulation B emits output token one at the end of prefill. The live demo separates reasoning and answer text. Reasoning consumes the output budget. |
| Single GPU | Follow a request from a Service to one model server | Qwen3.5-0.8B, startup logs, a successful stream, and lesson 01 metrics. Models already exist on shared storage; attendees do not download them. |
| Batching | Explain when a freed sequence slot can accept work | Simulation A compares static and continuous admission with identical requests. Occupancy measures sequence slots only. |
| Memory | Separate weights, runtime reservation, and KV capacity | Simulation C illustrates one full-attention cache and conservative reservations. The sequence limit does not guarantee enough KV capacity. |
| Tensor parallelism | Explain how one model spans two GPUs within a Pod | Lesson 02 uses bfloat16 (BF16) Muse Glimmer 30B with TP 2. Its single Pod places both GPUs on one node. TP can span nodes with suitable communication links. |
| Pipeline parallelism | Distinguish layer stages from tensor splitting | Lesson 03 keeps the Muse checkpoint fixed, uses TP 1 and PP 2, and requires different nodes. Only the leader serves HTTP. |
| Disaggregation | Distinguish request phases from model-layer stages | Lesson 04 switches to Gemma 4 12B IT so each worker holds a full model on one GPU. NVIDIA Inference Xfer Library (NIXL) transfers KV cache over TCP with CPU buffers. |
| Performance | Compare throughput and latency over explicit intervals | Simulation D uses synthetic time. Live engine, frontend, browser, and traffic-client measurements retain their own definitions. |

The TP-to-PP comparison changes parallelism and node placement. Lesson 04 changes both the model and serving system. These comparisons do not isolate one performance variable. TCP transfer and low concurrency can make disaggregation slower.

Compare disaggregation with a combined worker using the same model and workload. Lesson 03 is not that baseline. PP can also run within one node; lesson 03's required anti-affinity creates the two-node placement.

## Hardware along the ladder

Teach hardware where a lesson depends on it, not in a separate chapter. Each load window introduces the hardware fact that the next hands-on part makes visible.

| Load window | Hardware topic | Lesson connection |
| --- | --- | --- |
| Lesson 01 | One GPU's memory holds the weights, runtime allocations, and KV cache | Lesson 01 gives vLLM 25% of one L40. The startup logs report weight memory and KV-cache capacity. |
| Lesson 02 | Model size in bytes against GPU memory, and links between GPUs in one node | The BF16 checkpoint stores about 59.6 GB, and one L40 has 48 GB. TP exchanges data between GPUs at every layer, so both GPUs share a node. |
| Lesson 03 | Networks between nodes, NVLink domains, and why GPUs are not fungible | PP sends activations only between stages, so it tolerates a slower link than TP. Contrast TCP, RDMA over InfiniBand or RoCE, and rack-scale NVLink. |
| Lesson 04 | The KV transfer path between workers | NIXL uses UCX over TCP with CPU buffers, without RDMA or CUDA IPC. A faster transport changes the cost of disaggregation. |

Lesson 03 has the longest measured load, so it holds the largest hardware block. It also closes the intro's claim that GPUs are not fungible. Details of specific GPU generations, such as Hopper, Blackwell, and Grace, are optional unless they support a ladder step.

The repository does not record the interconnect of the workshop nodes. NVIDIA describes the L40 as a PCIe card with 48 GB of GDDR6 memory and no NVLink. During rehearsal, run `nvidia-smi topo -m` on a node and check for an RDMA network before slides describe either.

## Live observations beside simulations

Keep live values separate from simulated values. Label every live value with its source, model, and measurement interval. Do not calibrate the teaching model from a workshop run.

| Simulation | Live counterpart | Required explanation |
| --- | --- | --- |
| A: Continuous batching | Lesson 01 traffic at concurrency 1 and 4; running requests, waiting requests, and token throughput in Grafana | Each traffic run lasts one minute. The fixed prompt can reuse cached prefixes. A concurrency comparison is an observation, not an isolated benchmark. |
| B: Prefill and decode | Lesson 04 worker logs, each worker's `generate` counter, and a successful streamed response | The simulator excludes KV transfer. NIXL initialization or a counter alone does not prove correct generated output. |
| C: KV cache | Startup capacity reports and the overview's KV-cache use panel | Gemma 4 12B uses hybrid attention. Quote its capacity as observed engine output; do not derive it with Simulation C's full-attention formula. |
| D: Latency and throughput | Engine histograms, Dynamo frontend metrics, browser timing, and `traffic.py` summaries | Each source measures a different interval. State the source before comparing values. |

The demo measures time from browser submission to the first reasoning or answer text. Its output count includes reasoning. Its overall output rate divides completion tokens by elapsed browser time through stream completion, including the initial wait.

The traffic client sums completion-token usage from completed requests and divides by actual elapsed run time. Canceled requests do not count as failures. The client does not report TTFT or TPOT.

Engine and frontend percentiles are histogram estimates over the selected dashboard window. The engine's inter-token latency histogram is different from the simulator's per-request TPOT. Keep prefill and decode worker metrics separate because both can report prompt tokens for one request. Lesson 03 exposes engine metrics only on the leader; GPU metrics include both Pods.

## Attendee flow and presenter handoffs

Use the committed lesson READMEs for terminal procedures. Every workspace terminal inherits `NAMESPACE`. Reuse one terminal for lesson commands and `VLLM_BASE_URL`. The workspace and workload namespace differ. The demo's localhost URL refers to the workspace, not an attendee laptop.

Before each new deployment, stop the previous demo, delete the previous lesson resources, and confirm GPU quota usage returns to `0/2`. The old `vllm` Service conflicts with LWS discovery. Priority preemption does not bypass quota admission or replace this cleanup.

Apply each manifest after cleanup, then explain the matching concept while Pods load. Before traffic starts, confirm a streamed request succeeds. The four lessons contain five one-minute traffic runs in total. Include dashboard discovery, refresh delays, and model readiness in rehearsal time.

### Intro and live follow-along

Before the session, the driving presenter deploys lesson 01 in their own workload namespace. At minute 0, the presenter streams a reply in the demo and points at time to first token. During workspace sign-in, the presenter stops the demo and deletes the lesson 01 resources. At minute 5, the presenter applies lesson 01 again with the attendees. Keep a recording of the hook as its backup.

During each hands-on part, the driving presenter follows the lesson live in their own workspace on the projector. The other presenter helps attendees in the room. If the live workspace fails, return the projector to the "Your turn" slide.

### Lesson transitions

Each transition between lessons uses the same sequence:

1. End the hands-on part with the traffic run. Show Grafana on the projector during the run.
2. Debrief the lesson with the values that attendees just observed. The debrief ends with the next lesson's problem.
3. Show the transition slide. It states that problem in one sentence. Attendees stop the demo, clean up, confirm GPU quota usage of `0/2`, and apply the next manifest.
4. While Pods load, teach the next concept. End with what to look for in the logs.
5. Show the "Your turn" slide with the lesson path, section numbers, what to look for, and time limit. The slide does not repeat the README commands, so it stays correct when a lesson changes.

The debrief comes before the cleanup, so the deck never returns to a lesson after the next lesson has started. This costs about one minute of each load window. Lesson 03 has the least margin: about 280 seconds of loading against about five minutes of teaching.

Each debrief introduces the next lesson's problem:

| Debrief | Next problem |
| --- | --- |
| Lesson 01: concurrency 4 completed more requests than concurrency 1, and vLLM's memory budget was 25% of GPU memory | Muse Glimmer 30B in BF16 does not fit on one L40 |
| Lesson 02: two GPUs exchange data at every layer, and the single Pod places them on one node | Two free GPUs can be on different nodes |
| Lesson 03: the model is split by layers, and only the leader serves HTTP | A request can be split by phase instead |
| Lesson 04: prefill and decode run on separate GPUs, and KV transfer over TCP can make this slower | When each serving shape pays off, in latency and throughput |

Each workspace terminal starts with `NAMESPACE` set to the attendee's workload namespace. Every lesson uses that value to build `VLLM_BASE_URL`. Attendees do not need to set `NAMESPACE` when they open a new terminal. Each lesson starts from a clean workload namespace, so a late attendee can skip to the current lesson after cleanup.

Use these API Services consistently:

| Lesson | API Service | Distinction |
| --- | --- | --- |
| 01 and 02 | `vllm` | Deployment-backed API |
| 03 | `vllm-leader` | LWS reserves `vllm` for headless discovery |
| 04 | `vllm-frontend` | Operator-created Dynamo frontend |

Presenter A introduces the question and hands control to Presenter B for the prepared interaction. Presenter B explains the model limits and returns control after reset. These role assignments are provisional. Both presenters use the authoritative projected window described in the architecture.

For each demonstration, prepare a named preset, a spoken learning objective, a short sequence of interactions, a reset cue, and a backup cue. Label synthetic values visibly. Explanatory reveals must remain separate from simulation steps. Keep labels readable with reduced motion enabled.

## Mapping the source outline

The ignored `draft/flow.md` and `draft/hands-on-flow.md` are source material. Preserve them. The committed lessons define the current lab procedure when an outline differs.

| Outline topic | Destination and treatment |
| --- | --- |
| Inference and client request anatomy | Request chapter; prompt history, context length, input and output lengths, and reasoning budget |
| Model size, dtype, and models that do not fit | Single-GPU and TP chapters; explain the selected BF16 model without adding a quantization lab |
| Engine startup and kernel autotuning | Startup-log explanation; model files are preloaded, and lesson 01 uses eager execution |
| Server request anatomy, batching, and concurrency | Simulations A and B, connected to lesson 01's load comparison |
| KV capacity, sequence length, and concurrency | Simulation C; qualify the outline's proportionality claim with cache layout, block allocation, and reservations |
| Hardware, GPU topology, and parallelism | Lesson load windows in [Hardware along the ladder](#hardware-along-the-ladder); qualify claims by the actual hardware and placement configuration |
| Runtime and framework survey | Brief context for vLLM and Dynamo; broader vendor comparisons stay in optional material |
| Performance metrics and operational challenges | Simulation D, dashboards, finite GPU quota, cleanup, and readiness |
| Tool calling, expert parallelism, and goodput | Optional appendix or follow-up; they do not displace the four labs |

## Review before full narrative integration

Both presenters must review the agenda, role assignments, and control-window arrangement. Rehearse from a fresh workspace and record which traffic runs to skip if the session overruns. Individual lesson checks do not establish the combined session duration.

The root abstract still promises CPU deployment. Align that sentence during narrative integration with the approved single-GPU start. Preserve the abstract in this architecture change.

Prepare dashboard captures during connected rehearsal because monitoring history is temporary. Confirm that the deployed workspace bundle matches the lesson revision being taught. A source change does not update an existing workspace.
