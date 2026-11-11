# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This repository holds the hands-on material for the KubeCon NA 2026 tutorial "Minting Your Own Tokens" (the root `README.md` is the talk abstract). Attendees follow numbered lessons in `tutorial/`, and each lesson deploys vLLM on Kubernetes with a different parallelism or serving setup. The tutorial has no build step. The Python demo server and traffic client use only the standard library.

## Presentation development

The local Slidev deck in `presentation/` is separate from the cluster-backed tutorial. Read [docs/architecture.md](docs/architecture.md) for simulation contracts, [docs/narrative.md](docs/narrative.md) for the teaching sequence, and [presentation/README.md](presentation/README.md) for commands and the rules for interactive components. Planner holds the backlog; do not copy it into repository documentation.

Run the deck and the engine tests from `presentation/`. Slidev 53 needs Node.js 22.12 or later.

```bash
bun install --frozen-lockfile
bun run dev
bun test
```

- Keep presentation dependencies under `presentation/`. Use Bun and commit `bun.lock`.
- Keep engine transitions in plain deterministic TypeScript under `presentation/simulator/`. Vue owns controls, playback timers, and rendering. Slidev owns navigation and explanatory clicks. Animation timing must not change engine outcomes.
- Operate simulations only in the projected window. Slidev synchronizes navigation between the presenter and audience windows, but not component state. Assign one integration owner for engine interfaces, `package.json`, `bun.lock`, `slides.md`, and CI before parallel edits.
- Disable remote fonts and bundle required media locally. The built deck must load through a local HTTP server without external requests. Live labs and dashboards retain their network requirements.
- Test engine behavior with Bun's test runner (`bun test`) against hand-written traces. Add Playwright checks for real controls, lifecycle, and offline loading. Keep the Python suite independent.
- Start deployment teaching with lesson 01 on one GPU. CPU deployment is excluded. Preserve lesson invariants and keep live measurements separate from illustrative simulated values.

## Commands

Run all tests (no dependencies to install):

```bash
python3 -m unittest discover -s tests -v
```

Run one test:

```bash
python3 -m unittest tests.test_streaming_demo.StreamingDemoTest.test_model_name_is_escaped_in_the_page
```

The tests start real HTTP servers on loopback. `DemoServerTest.test_ctrl_c_exits_cleanly` starts the actual demo on port 8080, so that port must be free. In a sandbox that blocks local port binding, every test fails: most with `PermissionError: [Errno 1] Operation not permitted`, and the Ctrl+C test with `Demo server did not start within five seconds.` Those failures come from the environment, not from the code.

Run opt-in live vLLM version checks with `tests/vllm_live.py`. Use an idle workload namespace with the hydrated model PVC. See [tests/README.md](tests/README.md) for target selection, candidate image overrides, and cleanup behavior.

Run the demo against any OpenAI-compatible vLLM endpoint:

```bash
VLLM_BASE_URL=http://localhost:8000 python3 tutorial/server/demo.py
```

Attendees apply the manifests from inside each lesson folder with `kubectl apply -f vllm.yaml` (lessons 01 to 03) or `kubectl apply -f dynamo.yaml` (lesson 04). Local work on this repository does not need a cluster.

## Lessons

| Lesson | Model | Kubernetes shape |
| --- | --- | --- |
| `tutorial/01-vllm` | Qwen3.5-0.8B | Deployment, one GPU |
| `tutorial/02-tensor-parallel` | Muse Glimmer 30B, BF16 | Deployment, one Pod with two GPUs, TP 2, `mp` executor |
| `tutorial/03-pipeline-parallel` | Same Muse Glimmer revision | LeaderWorkerSet of size 2, one GPU per Pod on different nodes (required anti-affinity), TP 1, PP `$(LWS_GROUP_SIZE)` |
| `tutorial/04-prefill-disaggregation` | Gemma 4 12B IT, BF16 | DynamoGraphDeployment with a CPU frontend and two full-model vLLM workers, one GPU for prefill and one for decode |

In lesson 03 the worker runs `--headless`, and the Service selects only `role: leader`. The leader and worker templates are near copies; they differ only in the `role` label, `--headless` versus `--host`/`--port`, and the ports and probes that only the leader has. Change both templates together.

### Invariants across the manifests

- Every lesson creates a Deployment, LeaderWorkerSet, or DynamoGraphDeployment named `vllm`. Lessons 01 and 02 use an API Service named `vllm` on port 8000. Lesson 03 uses `vllm-leader` on port 8000, because LWS reserves `vllm` for its headless discovery Service. Lesson 04 uses the operator-created `vllm-frontend` Service on port 8000. The demo always listens on port 8080. Clean up the previous lesson before continuing.
- Rollouts must not request extra GPUs. The Deployments use `strategy: Recreate`, the LeaderWorkerSet uses `maxSurge: 0`, and Dynamo propagates `nvidia.com/deployment-strategy: Recreate` to its components. Before applying a changed lesson 04 manifest, delete its DynamoGraphDeployment and wait for GPU quota usage to return to `0/2`. A live Dynamo 1.6.0 update can replace the new workers again and hit quota errors before it settles.
- Lessons 01 to 03 use the same `vllm/vllm-openai:v0.33.0` image pinned by the same SHA-256 digest. Change that digest in all three manifests at once. Lesson 04 uses a separate Dynamo 1.6.0 runtime with bundled vLLM 0.31.0. Keep its image digest identical across all three components.
- The model argument is a pinned revision path, `/models/<org>/<name>/<revision>`, and `--served-model-name` is the Hugging Face ID. The lesson README must export the same ID as `VLLM_MODEL` before it starts the demo.
- Models load offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`) from the organizer's shared `workshop-models` PVC. Keep `readOnly: true` on both the PVC volume source and the volume mount, because cluster admission rejects the Pod otherwise. Writable caches go under `/tmp`.
- Pods run as non-root UID 2000 with all capabilities dropped and the `RuntimeDefault` seccomp profile, and mount a memory-backed `emptyDir` at `/dev/shm`.

In lesson 04, change both worker configurations together. Keep the model, dtype, context, and KV-cache settings aligned. Preserve their distinct `prefill`/`decode` modes and `kv_producer`/`kv_consumer` connector roles. CPU transfer buffers and `UCX_TLS=tcp,cuda_copy` avoid RDMA and CUDA IPC requirements. Keep `--disable-hybrid-kv-cache-manager` on both workers: Gemma's hybrid allocation produces corrupt output with CPU transfer buffers in this runtime. Sliding-window attention remains enabled. All three Pods mount the model files because the frontend also needs the tokenizer. Keep ServiceAccount token mounting enabled for Kubernetes discovery; the operator supplies the namespace-scoped discovery permissions and mounts shared memory.

### Lesson transitions: explicit cleanup

Decision recorded on 2026-10-24: keep explicit cleanup between lessons. We considered increasing `PriorityClass` values so each lesson could preempt the previous lesson, and rejected the approach for these reasons:

- GPU quota is checked before scheduling. At `2/2` GPUs, the next GPU Pod is rejected before the scheduler can attempt preemption. Higher priority does not bypass quota.
- Preemption removes Pods, but leaves their workload controllers and Services. Controllers attempt to recreate the Pods. The old `vllm` Service also conflicts with lesson 03's LWS discovery Service.
- Preemption can affect lower-priority Pods in other workload namespaces. An attendee on a later lesson could disrupt another attendee on an earlier lesson.
- Preemption happens only when scheduling requires it. If enough GPUs are free, both lessons can remain running, so priority does not guarantee replacement.

Delete the previous lesson's resources and confirm GPU quota usage returns to `0/2` before deploying the next lesson.

References: [Kubernetes resource quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/), [Pod priority and preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/), and [ReplicaSet behavior](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/).

## Streaming demo (`tutorial/server/`)

- `demo.py` runs a `ThreadingHTTPServer` on `127.0.0.1:8080`. `GET /` serves `demo.html` after it replaces `{{MODEL_NAME}}` (HTML-escaped), `{{MAX_OUTPUT_TOKENS}}`, and `{{DEFAULT_OUTPUT_TOKENS}}`. `POST /chat` validates the prompt, `max_tokens`, and `temperature`, sends a streaming `/v1/chat/completions` request to vLLM, and copies the server-sent events line by line to the browser.
- `demo.py` reads `demo.html` from its own directory, so keep the two files together.
- The `DemoHandler` class body reads its configuration when the module loads. `VLLM_BASE_URL` is required, and the import fails without it. `VLLM_MODEL` defaults to `Qwen/Qwen3.5-0.8B`. `VLLM_MAX_OUTPUT_TOKENS` defaults to 512 and must be a positive integer.
- Keep these behaviors, because the tests assert them: the model name is HTML-escaped, opening the page sends no model request, and the stream response carries `Cache-Control: no-store, no-transform` and `X-Accel-Buffering: no` so that proxies do not buffer it.
- The tests load the module with `runpy.run_path` under `patch.dict("os.environ", ..., clear=True)`, then change class attributes on the handler to vary the configuration. A fake vLLM upstream runs as a real loopback server. Follow this pattern rather than mocking the network.

## Traffic client (`tutorial/server/traffic.py`)

- The client reads `VLLM_BASE_URL` and `VLLM_MODEL`. It sends a fixed prompt with a 256-token output limit for 60 seconds at concurrency 1 or 4.
- The deadline and Ctrl+C stop new requests and interrupt active sockets. Canceled requests are excluded from failures. The summary uses actual completion-token usage and elapsed time.
- Exit status is 1 for request failures, 130 for Ctrl+C, and 2 for invalid configuration. Tests in `tests/test_traffic.py` use a real loopback server, including stalled and trickling responses.

## Attendee environment

- Attendees use a browser-based VS Code workspace that runs inside the cluster, in a namespace different from their workload namespace. Lessons 01 and 02 set `VLLM_BASE_URL` to `http://vllm.${NAMESPACE}.svc:8000`. Lesson 03 uses `http://vllm-leader.${NAMESPACE}.svc:8000`. Lesson 04 uses `http://vllm-frontend.${NAMESPACE}.svc:8000`. Every `localhost` URL refers to the workspace, not to a laptop.
- A new workspace terminal starts in `tutorial/` and inherits `NAMESPACE` with the attendee's workload namespace. The lesson steps reuse one terminal across lessons (for example `cd ../02-tensor-parallel`) to preserve the current directory and `VLLM_BASE_URL`.
- A bundle script in a separate companion repository (gitignored here as `kubecon-na26-tutorial-private/`) copies the tutorial files into each workspace. That script lists every file under `tutorial/` by path. When you add, move, or rename a file under `tutorial/`, tell the user that the bundle list must change too.

## Lesson README conventions

- Notes and cautions are blockquotes with an emoji and a bold label: `> ℹ️ **Note:**` and `> ⚠️ **Caution:**`.
- Links to vLLM documentation are pinned to the image version, for example `https://docs.vllm.ai/en/v0.33.0/...`.
- When you add a lesson, add it to the list in `tutorial/README.md` and to the "Next exercise" link at the end of the previous lesson.

### Code blocks

Attendees copy each code block and paste it into a terminal as one unit. Put at most one command that prints output in a code block, so that the attendee can match each output to its command. Follow each block with a sentence that tells the attendee what output to expect. Commands that print nothing, such as `export` and `cd`, can share a block with the command that uses them. A command that continues across lines with `\` counts as one command.

Do not group these commands, because both commands print output:

```bash
kubectl get pods
kubectl get svc
```

This grouping is correct, because only the last command prints output:

```bash
export POD=foo
kubectl get pods "${POD}"
```

### Instruction language

Write lesson instructions in the style of ASD-STE100 Simplified Technical English, so that attendees can follow each step while they work in a terminal during a timed session:

- Write each instruction as a command: "Apply the manifest.", not "Now you can apply the manifest."
- Give one instruction in each sentence.
- Put the condition before the command: "If the Pod is `Pending`, read the events."
- Keep an instruction to 20 words or fewer, and a descriptive sentence to 25 words or fewer.
- Use the active voice when the actor is known: "Kubernetes deletes the Deployment."
- Use one term for one thing in every lesson. For example, always write "workload namespace", "Pod", and "Service" for the same objects.
- Put the expected result immediately after the step that produces it, so that the attendee can confirm that the step worked.
- Put a caution in the step that it applies to, before the action that can cause the problem.
