/* main.c - run the lifted VBRUN300.
 *
 * Hand-written, so it lives here and not under work/, which is generated and
 * gitignored in its entirety.
 *
 * VBRUN300 is a DLL: it has no stack of its own (its NE ss:sp is 0:0), so
 * gen_image.py --stack maps one. DS points at a DATA segment; the NE header's
 * auto-data field is 0, so segment 100 -- the first and larger of the two -- is
 * an assumption, stated here rather than buried.
 *
 * Unimplemented imports are not fatal: each announces itself once, purges its
 * PASCAL arguments correctly and returns AX=0, so the run carries on and
 * reports which Win16 APIs the interpreter actually reaches.
 */
#include "segments.h"
#include "mem_layout.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef VBRUN_IMAGE_PATH
#define VBRUN_IMAGE_PATH "work/mem_image.bin"
#endif
#define DGROUP 100

static CPU cpu;
static uint32_t sel_base[0x10000];

int main(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "--selftest") == 0) {
        printf("vbrun: selftest -- calling an unlifted target, expecting abort\n");
        seg006_0B62(NULL);
        printf("vbrun: SELFTEST FAILED - stub returned instead of aborting\n");
        return 1;
    }

    const char *img = (argc > 1) ? argv[1] : VBRUN_IMAGE_PATH;
    FILE *f = fopen(img, "rb");
    if (!f) { fprintf(stderr, "cannot open %s\n", img); return 2; }

    cpu.mem = calloc(1, RECOMP_IMAGE_SIZE);
    if (!cpu.mem) { fprintf(stderr, "out of memory\n"); return 2; }
    size_t n = fread(cpu.mem, 1, RECOMP_IMAGE_SIZE, f);
    fclose(f);
    printf("image: %zu / %u bytes\n", n, (unsigned)RECOMP_IMAGE_SIZE);

    /* selector -> flat base. The lifter normalises every relocated selector to
       its NE segment index, so index n maps to SEG_SEGMENT_BASE[n]; every other
       selector lands in the isolated guard region. */
    for (unsigned s = 0; s < 0x10000; s++) sel_base[s] = RECOMP_GUARD_BASE;
    for (unsigned s = 0; s <= RECOMP_NUM_SEG; s++) sel_base[s] = SEG_SEGMENT_BASE[s];
    cpu.sel_base = sel_base;

    cpu.ds = cpu.es = DGROUP;
    cpu.ss = RECOMP_STACK_SEG;
    cpu.sp = RECOMP_STACK_SP;
    cpu.cs = 45;
    cpu.di = DGROUP;          /* hInstance */
    cpu.flags = 0x0202;

    printf("entry: seg45:0000 (THUNRTMAIN, ordinal 100)   ds=%u ss=%u:%04X\n",
           (unsigned)cpu.ds, (unsigned)cpu.ss, (unsigned)cpu.sp);
    printf("note: the NE header entry is seg%u:%04X, which is `mov ax,sp; retf`.\n",
           (unsigned)RECOMP_ENTRY_SEG, (unsigned)RECOMP_ENTRY_IP);
    fflush(stdout);

    /* Ordinal 100, THUNRTMAIN -- exactly what EMPIRE.EXE's nine bytes call. */
    seg045_0000(&cpu);

    printf("\nreturned from THUNRTMAIN: ax=%04X dx=%04X sp=%04X\n",
           cpu.ax, cpu.dx, cpu.sp);
    return 0;
}
