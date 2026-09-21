"""build.py - compile the lifted VBRUN300 sources.

Not a substitute for CMake; this is the bring-up loop -- compile everything,
bucket the diagnostics, print what is left. Parallel because 99 translation
units of lifted C is a few minutes single-threaded.
"""
import os, re, subprocess, sys, time, collections
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC  = os.path.join(ROOT, 'work', 'src')
OBJ  = os.path.join(ROOT, 'work', 'obj')
INC  = os.path.join(ROOT, 'work', 'runtime')
GCC  = r"%MSYS2_ROOT%\mingw64\bin\gcc.exe"
os.environ['PATH'] = r"%MSYS2_ROOT%\mingw64\bin;" + os.environ['PATH']
os.makedirs(OBJ, exist_ok=True)

FLAGS = ['-c', '-O2', '-g1', '-std=c11', '-I', INC, '-Wall',
         '-Wno-unused-variable', '-Wno-unused-label',
         '-Wno-unused-but-set-variable', '-Wno-unused-function']

def compile_one(path):
    base = os.path.splitext(os.path.basename(path))[0]
    obj = os.path.join(OBJ, base + '.o')
    p = subprocess.run([GCC] + FLAGS + [path, '-o', obj],
                       capture_output=True, text=True)
    return base, p.returncode, p.stderr

sources = sorted(f for f in os.listdir(SRC) if f.endswith('.c'))
t0 = time.time()
with ThreadPoolExecutor(max_workers=os.cpu_count()) as ex:
    results = list(ex.map(compile_one, [os.path.join(SRC, f) for f in sources]))

failed = [(b, e) for b, rc, e in results if rc != 0]
diags = collections.Counter()
for b, rc, err in results:
    for line in err.splitlines():
        m = re.search(r'\b(error|warning): (.*)', line)
        if m:
            diags[m.group(1) + ': ' + re.sub(r"'[^']*'", "'X'", m.group(2))] += 1

print(f"{len(sources)} translation units, {time.time()-t0:.1f}s")
print(f"  compiled: {len(sources)-len(failed)}   FAILED: {len(failed)}")
objs = [f for f in os.listdir(OBJ) if f.endswith('.o')]
print(f"  objects:  {len(objs)}  ({sum(os.path.getsize(os.path.join(OBJ,f)) for f in objs):,} bytes)")
if diags:
    print("  diagnostics:")
    for d, n in diags.most_common(12):
        print(f"    {n:5d}  {d}")
for b, e in failed[:5]:
    print(f"\n--- {b}"); print("\n".join(e.splitlines()[:8]))
sys.exit(1 if failed else 0)
