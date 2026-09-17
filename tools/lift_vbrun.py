"""lift_vbrun.py - lift every VBRUN300.DLL code segment to work/src/segNNN.c.

EMPIRE.EXE is VB3 p-code and has no x86 to lift; the machine code is all in the
interpreter, so the interpreter is what gets lifted. Same shape as catz, where
the engine is a 16-bit NE DLL and the game is what it loads.
"""
import os, sys, contextlib, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PCRECOMP = r"G:\recomp\pc\tools\tools"
for p in (os.path.join(PCRECOMP, 'ne'), os.path.join(PCRECOMP, 'disasm'),
          os.path.join(PCRECOMP, 'lift')):
    sys.path.insert(0, p)

# Win16 ordinal names come from the toolbox-level map (tools/ne/win16_imports.json,
# built by idt_to_json.py). Set PCRECOMP_WIN16_IMPORTS to override per project.

from ne_parse import parse_ne
import ne_lift
# PREFIX stays 'recomp', matching runtime/win16/cpu.h

DLL = os.path.join(ROOT, 'original', 'ex', 'VBRUN300.DLL')
SRC = os.path.join(ROOT, 'work', 'src')
os.makedirs(SRC, exist_ok=True)

ne = parse_ne(DLL)
code = [s for s in ne.segments if s.is_code]
print(f"VBRUN300.DLL: {len(code)} code segments, {ne.total_code_size:,} bytes")

ok = fail = 0
errors = []
t0 = time.time()
for s in code:
    out = os.path.join(SRC, f'seg{s.index:03d}.c')
    try:
        with open(out, 'w', encoding='utf-8', newline='\n') as f:
            with contextlib.redirect_stdout(f):
                ne_lift.lift_segment(ne, s.index)
        ok += 1
    except Exception as e:
        fail += 1
        errors.append((s.index, f"{type(e).__name__}: {e}"))
        try: os.remove(out)
        except OSError: pass

print(f"lifted {ok}/{len(code)} segments in {time.time()-t0:.1f}s, {fail} failed")
for idx, e in errors[:25]:
    print(f"  seg {idx:3d}: {e}")
