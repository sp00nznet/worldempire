# Roadmap

## Now

**A Win16 memory manager.** `THUNRTMAIN` reaches `KERNEL.GlobalHandle`, gets
AX=0 from the stub and takes its failure branch out through `INT 21h AH=4Ch`.
`GlobalAlloc`/`GlobalLock`/`GlobalHandle`/`GlobalFree` backed by real
selector-mapped handles is what gets past init. This is a phase, not a patch --
catz's `win16_impl.c` is 106 KB for the same reason.

## Next

- **Drive down the 234 unresolved call targets** (1.59% of 14,731). Each is a
  target a linear sweep could not align to an instruction boundary. They abort
  loudly rather than return, so they surface as soon as they are reached.
- **The 123 unhandled instructions**, mostly data decoded as code (`? di`,
  `into`, `outsd`) plus about 20 real x87 gaps.
- **Indirect dispatch.** `call bx` and `call far [bp-4]` need a
  (segment, offset) -> function table; today they abort.
- **A conformance harness** per house style: a pass/fail count against a fixed
  corpus, tracked over time, failing on regression rather than only on total
  failure. The two ctest cases are the seed, not the harness.

## Deferred

- **The VB3 p-code side.** Nothing has interpreted a token yet, and nothing
  should until the interpreter runs -- the whole point of this target is that
  the opcode semantics are the interpreter's x86, so they never need guessing.

## Out of scope

- A standalone VB3 p-code decoder as a separate front end. The interpreter
  route has not been exhausted, and while it holds, a second front end is work
  that does not need to exist.
- Redistributing anything derived from the binary. The tool ships; the output
  never does.
