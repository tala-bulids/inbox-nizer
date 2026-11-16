# Final memory optimization — 4 November 2026

**Completed: PASS at 333.140625 MiB.** See [the final measured verdict](#final-measured-verdict--pass) below. Earlier preparation and pending-run statements are preserved in chronological context; no further optimization or qualification cycle is pending.

Scope: one focused allocation change and one final private Linux qualification.
The existing 400 MiB peak target, 512 MiB hard limit, 0.1 CPU and zero swap remain.

## Measured contributors

The previous real Ubuntu run at source `24c953b` completed all inference but peaked
at 524296192 bytes (500.0078125 MiB). Its cgroup peak at readiness was 334647296
bytes (319.14453125 MiB); the 512-token encoder probe recorded the final high peak.
Classification added little resident memory. These are container totals, including
the observer, not just Python RSS.

Local ONNX Runtime 1.31.0 operator profiling of the same hash-verified artifact
showed 12 MiB attention outputs with shape [1,12,512,512] in MatMul, scaling, mask
addition and Softmax. The largest persistent initializer is the 96,014,208-byte
INT8 embedding table. Isolated Windows observations: tokenizer resident increase
about 43 MiB; session resident increase about 124 MiB; initialization high-water
about 302 MiB. Windows profiling identifies tensors; it does not qualify Linux.

Extended ORT graph optimization was examined locally but **not adopted**: the
512-token output differed by max absolute 0.007711 and cosine 0.998942. The serving
graph remains BASIC, single-threaded with ORT CPU arena and memory patterns off.
Weights, preprocessing, token budget, model identity and inference code are unchanged.

## Focused change

`deploy/with-showcase-memory.sh` sets the following before Python starts, and is
shared by the existing Free start script and qualification Docker entrypoint:

- `MALLOC_ARENA_MAX=2`
- `MALLOC_MMAP_THRESHOLD_=131072`
- `MALLOC_TRIM_THRESHOLD_=131072`

The hypothesis is that glibc's dynamic allocation thresholds and per-thread heaps
retain large transient encoder allocations. Fixed thresholds let large freed
buffers return to the OS and bound allocator arenas. This changes allocation only;
it does not avoid the full-token stress request or remove any feature. See
[glibc's allocator documentation](https://sourceware.org/glibc/manual/latest/html_node/Memory-Allocation-Tunables.html).
Additional cgroup memory.stat and pre-maximum snapshots expose anonymous/file/kernel
memory and when the peak grows. No profiling trace is enabled in the capacity run.

## Verification before final run

Focused tests: **38 passed**. All isolated showcase tests: **105 passed**,
including the existing real private classifier integration. Commands:

```text
python -m pytest --confcutdir=showcase showcase/tests/test_memory_launcher.py showcase/tests/test_free_runtime.py showcase/tests/test_linux_qualification.py -q -p no:cacheprovider
python -m pytest --confcutdir=showcase showcase/tests -q -p no:cacheprovider
```

The initial sandbox could not launch Git's existing shell; a subsequent run passed
both shell tests but hit a full disk writing pytest cache. After removing only this
task's disposable profiler traces, the authorized reruns above exited successfully.
The existing FastAPI/httpx deprecation warning remains unrelated.

The private workflow must compare actual QA/language/task aggregates with the prior
real Linux evidence (excluding timings), verify the allocator settings, and keep
the original resource gate. Final measured outcome is recorded after that one run;
this preparation is not a memory PASS. No Render change or deployment is authorized.

## Final measured verdict — PASS

Verified on 14 November 2026 from the existing final run completed on 4 November
2026 at 09:07 Arabia Standard Time. No second qualification or optimization cycle
was started. [Private workflow run 41783099933](https://github.com/tala-bulids/inbox-nizer-model-artifacts/actions/runs/41783099933),
job `126418958132`, completed successfully against application source
`73ebaf5a5693f2064628b9be935e3267af2fa702` and private workflow commit
`cb9398381a875669029efd120ac62128c5be7f10`.

| Measurement | Baseline | Final |
| --- | ---: | ---: |
| Container lifetime memory.peak, bytes | 524296192 | 349323264 |
| Container lifetime peak, MiB | 500.0078125 | 333.140625 |
| Engineering acceptance target, MiB | 400 | 400 |
| Hard memory limit, bytes | 536870912 | 536870912 |
| CPU quota / period | 10000 / 100000 | 10000 / 100000 |
| Swap allowance, bytes | 0 | 0 |
| Full encoder input, tokens | 512 | 512 |
| Full encoder latency, seconds | 3.896259 | 6.599054 |

Peak reduction: 166.8671875 MiB (33.372916%). Margin below the engineering target:
66.859375 MiB. Final worker process peak RSS was 374.55078125 MiB; this is a
different accounting measure from the container cgroup peak. The container exited
with code 0, `OOMKilled=false`, and zero `oom`/`oom_kill` events. Worker exit -15
is the probe's explicit termination after completing measurements, not an OOM.

The allocator policy was verified inside the measured environment. The unchanged
model, tokenizer and classifier files all passed their original SHA-256 checks.
QA, per-language and task quality aggregates exactly match the baseline when
timings are excluded: 20 QA cases, status accuracy 1.0, evidence-set accuracy 0.9,
citation precision 0.96875, literal grounding 1.0; 16 task messages, task F1 1.0,
deadline accuracy 1.0 and source-reference accuracy 1.0. Real classification,
Ask Mail, tasks, evidence, maximum inputs and frontend HTTP checks completed.
The four-request concurrency probe returned one HTTP 200 and three HTTP 429s,
within the unchanged bounded-admission contract.

Linux showcase regressions: **104 passed, 1 skipped**, with one existing
deprecation warning. The skip is the local-path private-classifier integration
test; the subsequent constrained stage loaded the hash-verified classifier and
performed real predictions. Downloader tests: **4 passed**. Evidence-guard tests:
**3 passed**. All workflow steps succeeded. The saved evidence explicitly records
`quality_unchanged=true` and `allocator_policy_verified=true`.

Exact sanitized summary was recovered from the private job log and saved locally
at `private_review/model-artifacts-qualification/results/2026-11-04-final-memory-qualification-summary.json`
(relative to the original workspace). Its SHA-256 is
`5467dcc30939c76f1f43845249d27fef2b79069af2227eb168eeec1c9adc3c46`.
Original qualification receipt SHA-256:
`c5f1ce692c01d62b0d10f5e45ca21540bfd20e09cc84ff15f1ecb27a08cec83d`.
Original real-inference receipt SHA-256:
`d7aaed30ca3b6a3abb690fb2b4a2a2824d66e2fe530a83f7f121f6d38ec8d331`.

**Free Hosting memory engineering verdict: PASS for this exact qualified candidate.**
Maximum-input latency increased; warm Ask and classification latencies remained
approximately 104 ms and 198 ms median. No model quality, token budget, features
or acceptance threshold was changed. No Render deployment, paid service or new
infrastructure was created. Optimization is complete.
