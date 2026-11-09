# Browser C/WASM feasibility spike

**Scope:** Approach 1, Modules 6 and 7. This spike selects a candidate and defines a repeatable correctness corpus; it does not connect the runner to the assessment page.

## Recommendation

Use Clang compiled to WebAssembly with a WASI Preview 1 runtime as the first implementation candidate. Pin the compiler wrapper and WASI shim versions, serve the compiler assets from the portal's own static origin, and run compilation and every program in workers.

This is a **conditional go for the internal pilot**, not a go-live approval. The candidate matches the required C language features on paper and has a complete browser execution path, but this workspace currently has no `node`/`npm` executable, so the real-WASM corpus and browser matrix could not be run here. Keep the server/client switch available until that verification is completed.

## Candidate comparison

| Candidate | Findings | Decision |
|---|---|---|
| Clang/LLVM WASM + WASI | Full C compiler, standard C headers, stdin/stdout, diagnostics, and generated WASM modules. The upstream `@live-codes/clang-wasm` package documents C11, worker use, a 28 MB compressed toolchain payload, and a C example using `scanf` and `qsort`. | Selected for the first pilot; validate this project’s corpus and browsers before student rollout. |
| Small self-hosted C compiler (`c2wasm`) | Its published C89 subset includes pointers, structs, dynamic allocation and basic formatted output, but the documented built-ins/libc do not cover the full `math.h`/`scanf` requirement. | No-go for this project’s required corpus. |
| TinyCC WASM / C interpreter | I did not find a project with enough primary documentation and repeatable browser evidence for the required C11, math, stdin, diagnostics and timeout matrix. | Do not choose without a separate successful spike. |

References: [Clang WASM package and browser API](https://www.npmjs.com/package/%40live-codes/clang-wasm), [its worker/runtime implementation](https://github.com/live-codes/clang-wasm), [browser WASI shim](https://github.com/bjorn3/browser_wasi_shim), [c2wasm supported subset](https://github.com/divsmith/c2wasm).

## Expected fit and limits

- Compile with C11 and the legacy execution service's `-O0 -Wall -Wextra` behavior where the WASM toolchain supports it.
- The toolchain has `scanf`/stdin, `printf`, strings, pointers, structs, recursion, dynamic memory and a C standard library. The corpus below includes these cases and `math.h`.
- A recent upstream measurement reports roughly 0.7 seconds for a warm C compile and a roughly 28 MB first toolchain download. These are upstream measurements, not measurements on this portal or campus devices.
- The compiler/runtime uses about 85 MB after decompression. Each student's browser bears this memory and compile cost; it does not add C compilation load to the Django host. Static asset caching is important when many students start at once.
- WASI is not a Linux environment. Non-standard OS headers/APIs, console-specific functions, network access, interactive input and some system calls are outside the supported contract. Test inputs are provided in full before execution.
- Clang/WASI and GCC are different toolchains. Undefined behavior and implementation-specific behavior can still produce different results. The server remains responsible for output comparison and final verdicts.
- Browser interruption is enforced by terminating a dedicated test-case worker. Each case starts in a fresh instance, so a runaway case does not block later cases. Compilation happens once for the source snapshot.
- Output is capped in the worker. WASM memory exhaustion is classified from the runtime trap where possible; this browser path does not yet provide a hard, portable per-program memory ceiling, so that remains a go-live check and limitation.

## Verification still required before go-live

1. Run all corpus cases through the pinned Clang/WASI toolchain and compare normal stdout with the expected outputs (and GCC baseline where both compile).
2. Confirm syntax diagnostics identify the source line and that an infinite loop is stopped within the configured limit.
3. Run the same cases in current Chrome, Edge, Firefox and Safari, including a low-memory device and first-load over a campus-like connection.
4. Measure cold/warm download, compile and execution time. Verify browser cache headers and same-origin static asset delivery.
5. Compare representative assessment question results against the legacy Docker/GCC path before disabling it.

The machine used for this implementation has GCC 14.2, but it does not currently provide `node` or `npm`. Run `python3 scripts/run-wasm-feasibility-baseline.py` for the GCC reference baseline. The browser package install/build and WASM execution checks require a Node/npm environment.
