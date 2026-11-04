# Final memory optimization — 4 November 2026

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
