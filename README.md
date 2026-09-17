# World Empire

**World Empire** (Viable Software Alternatives, 1994). Visual Basic 3. A
`pcrecomp` target -- but not the target you would first point it at.

## What the binary actually is

```
EMPIRE.EXE   411,785 bytes   NE, Microsoft linker 5.10, Windows
             15 segments, 114,025 bytes of "code"
             imported modules: VBRUN300     <- and nothing else
             relocations: 14 total, 13 of them internal
```

Two numbers settle it.

**One imported module.** Not KERNEL, not USER, not GDI -- just `VBRUN300.DLL`.
A native Windows program cannot draw a pixel or open a window without KERNEL,
USER and GDI. This one never calls them.

**14 relocations across 114 KB.** Native 16-bit code of that size carries
thousands; The Even More Incredible Machine has 4,743 across 197 KB in the
folder next door. Fourteen means almost nothing in those segments is machine
code at all.

The entry point is the whole program, and it is nine bytes:

```
1:0010  9A FF FF 00 00   call 0000:FFFF   ; RELOC: VBRUN300.100 (THUNRTMAIN)
1:0015  01 00                             ; dw 1
1:0017  FF FF                             ; RELOC: SELECTOR seg3:0000
```

Hand `VBRUN300.100` a pointer to segment 3 and get out of the way. Segments
4-15 are a 16-bit token stream -- `0x31F7 0x0010 / 0x31F7 0x0012 /
0x31F7 0x0014 / 0x31FD 0x0016`, one opcode walking consecutive local slots.
p-code. Pointing an x86 lifter at it produces garbage, confidently, and the
lifter has no way to notice.

## Where the x86 went

It did not go anywhere. It is in `VBRUN300.DLL`, in the same folder:

```
VBRUN300.DLL  398,416 bytes   NE, Microsoft linker 5.31, Windows DLL
              101 segments (99 CODE), 340,406 bytes of code
              relocations: 2,746
              imported modules: USER, KERNEL, GDI, KEYBOARD, WIN87EM
              exports: WEP, VARPTR, #100 THUNRTMAIN
```

That is an ordinary Win16 NE binary and `pcrecomp` reads it today -- `ne/` for
the container and the Win16 PASCAL purge table, `lift16` for the code. The
interpreter is not an obstacle between us and the game; **the interpreter is
the target**, and the p-code is the data it eats. Same shape as `catz`, where
the engine is a 16-bit NE DLL and the game is what it loads.

This is also why the VB3 opcode semantics do not need guessing. The dispatch
table lives in `VBRUN300.DLL` and the handlers are x86. Lift the interpreter
and the opcode table falls out of it -- the interpreter *is* the spec.

## The general rule, worth writing down

**`VBRUN*.DLL` as the only imported module means p-code, not x86** -- in *that
file*. It is a retarget signal, not a rejection: the machine code is in the
runtime DLL, and that DLL is usually an ordinary NE the existing front end
already handles. The check costs one `ne_parse.py` run, which now prints the
flag itself.

The same flag fires on `msbus/original/ex/KIDSCAT/CATALOG.EXE`, the Visual
Basic advertising catalogue bundled with The Magic School Bus.

Later VB (4, 5, 6) can compile to native x86, so an `MSVBVM60.DLL` import is
not automatically p-code; check before assuming either way. VB3 always is.

## Status

P2 -- the interpreter lifts, compiles and links. `VBRUN300.DLL` goes through
the stock pcrecomp NE pipeline with no project-specific lifter:

```
99/99 code segments          0 lift errors
226,480 lines of C           14,826 functions
2,106 Win16 import calls     300/300 resolved by name
123 unhandled instructions   mostly data decoded as code (? di, into, outsd)
```

```
100 translation units        0 compile errors, 0 warnings
21,321,841-byte binary       links and runs
234 unresolved call targets  1.59% of 14,731 -- each aborts, none return
```

The p-code side is untouched, and nothing calls into the guest yet.

**The purge gate is closed.** All 300 imports now have a PASCAL purge, so
`gen_win16_stubs.py` exits 0. The 133 that were missing were derived from the
documented prototypes rather than guessed: Win16 is PASCAL, so the purge is the
sum of the argument sizes -- 2 bytes per handle/int/BOOL/UINT, 4 per
LONG/DWORD/COLORREF/far pointer. `win16.py` stores the argument *types* and
derives the number, so a mistake reads as a wrong prototype, not as an
unfalsifiable integer.

The method was validated before being trusted: applied to the 163 purges
already in the table it reproduced 162, and the single disagreement turned out
to be a bug in the table -- `TrackPopupMenu` takes seven arguments, not six, so
16 rather than 14. An independent scan of real call sites agreed on 16.

Inferring purge from caller push runs was tried first and does not work (~86%,
and the minimum across call sites is worse). That reasoning is kept in
pcrecomp's `docs/PROJECTS.md` so it is not retried.

## Running it

The NE header entry (seg 45:00A0) is `mov ax, sp; retf` -- a 4-byte helper, not
LibMain. The real entry is ordinal 100, `THUNRTMAIN` at seg 45:0000, which is
what `EMPIRE.EXE`'s nine bytes call:

```
seg045_0000  (THUNRTMAIN)
  -> KERNEL.GLOBALHANDLE      unimplemented; stub purges, reports, returns AX=0
seg045_002A                   init check fails
seg045_009B
  -> INT 21h AH=4Ch           DOS terminate -- the runtime gives up deliberately
```

Lifted 16-bit code running a real Win16 init path and taking the documented
failure branch, because the stub correctly told it memory setup failed. The
p-code side is still untouched -- nothing has interpreted a VB token yet.

**Next**: a real Win16 memory manager. `GlobalAlloc`/`GlobalLock`/`GlobalHandle`
backed by actual selectors is what gets past init.

## Building

Everything under `work/` is generated and gitignored; none of it is
distributed. From a checkout with `original/ex/VBRUN300.DLL` in place:

```
python tools/lift_vbrun.py                                  # -> work/src/segNNN.c
python <pcrecomp>/tools/ne/gen_unresolved_stubs.py --src work/src \
       --out work/src/_unresolved_stubs.c
python <pcrecomp>/tools/ne/gen_segments_h.py --src work/src \
       --out work/runtime/segments.h --ne original/ex/VBRUN300.DLL
python <pcrecomp>/tools/ne/gen_win16_stubs.py original/ex/VBRUN300.DLL \
       --api work/runtime/runtime_api.h \
       --stubs work/runtime/win16/win16_stubs.c \
       --shims work/runtime/win16 --guard VBRUN300
python <pcrecomp>/tools/ne/gen_image.py original/ex/VBRUN300.DLL \
       --image work/mem_image.bin --header work/runtime/mem_layout.h \
       --stack 0x10000

cmake -S . -B work/cmake -G Ninja
cmake --build work/cmake
ctest --test-dir work/cmake
```

`python tools/build.py` is the faster bring-up loop: it compiles every unit in
parallel and buckets the diagnostics.

The one test checks the thing the whole bring-up rests on -- that an unlifted
target aborts instead of returning:

```
$ work/cmake/vbrun.exe --selftest
vbrun: selftest -- calling an unlifted target, expecting abort
[recomp] unreachable: seg006:0B62 was never lifted (data-in-code desync)
```

## Layout

```
worldempire/
  original/       win3_WorldEmp.zip
  original/ex/    extracted -- EMPIRE.EXE (p-code) + VBRUN300.DLL (the x86)
  analysis/       ne_parse output -- the evidence above
```

Part of the [pcrecomp](https://github.com/sp00nznet/pcrecomp) house style.
