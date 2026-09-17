cmake_minimum_required(VERSION 3.20)
project(worldempire_recomp VERSION 0.1.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)

# The lifted tree is generated, not committed. Run these first:
#   python tools/lift_vbrun.py
#   python <pcrecomp>/tools/ne/gen_unresolved_stubs.py --src work/src \
#          --out work/src/_unresolved_stubs.c
#   python <pcrecomp>/tools/ne/gen_segments_h.py --src work/src \
#          --out work/runtime/segments.h --ne original/ex/VBRUN300.DLL
set(GEN_SRC "${CMAKE_SOURCE_DIR}/work/src")
set(GEN_RT  "${CMAKE_SOURCE_DIR}/work/runtime")

file(GLOB LIFTED_SOURCES CONFIGURE_DEPENDS "${GEN_SRC}/*.c")
if(NOT LIFTED_SOURCES)
    message(FATAL_ERROR "No lifted sources in ${GEN_SRC}. Run tools/lift_vbrun.py first.")
endif()

# -O2 is a correctness requirement, not a preference. The lifter turns every
# intra-segment jump into `target(cpu); return;`, so a guest loop spanning
# lifted-function boundaries is host recursion. Only sibling-call optimisation
# turns it back into a loop; at -O0 a long guest loop blows any host stack.
# -g1 keeps function names and line tables so addr2line can symbolise the host
# backtrace that stands in for the guest call stack.
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-O2 -g1)

add_library(vbrun_segments STATIC ${LIFTED_SOURCES})
target_include_directories(vbrun_segments PUBLIC ${GEN_RT})
# Mechanically translated code trips these by construction, not by mistake.
target_compile_options(vbrun_segments PRIVATE
    -Wall -Wno-unused-variable -Wno-unused-label
    -Wno-unused-but-set-variable -Wno-unused-function)

# Win16 import stubs (generated) + the bring-up runtime (from pcrecomp).
add_library(vbrun_runtime STATIC
    "${GEN_RT}/win16/win16_stubs.c"
    "${GEN_RT}/win16/recomp_stubs.c")
target_compile_definitions(vbrun_runtime PRIVATE
    VBRUN_IMAGE_PATH="${CMAKE_SOURCE_DIR}/work/mem_image.bin")
target_include_directories(vbrun_runtime PUBLIC ${GEN_RT})

add_executable(vbrun "${CMAKE_SOURCE_DIR}/runtime/main.c")
# --whole-archive, not a plain link. A static library only pulls in the objects
# something references, and main.c references two functions -- so a plain link
# produced a 315 KB binary and proved nothing about the other 14,824. Forcing
# every object in is what makes "it links" mean the whole lifted tree resolves.
target_link_libraries(vbrun
    -Wl,--whole-archive vbrun_segments vbrun_runtime -Wl,--no-whole-archive
    m)
# Lifted frames are far fatter than the 16-bit originals. No ASLR so runtime
# addresses match file VAs and a backtrace pastes straight into addr2line.
target_link_options(vbrun PRIVATE
    -Wl,--stack,268435456
    -Wl,--disable-dynamicbase
    -Wl,--disable-high-entropy-va)

enable_testing()
# The one check the bring-up rests on: an unlifted target must abort, not return.
add_test(NAME unreachable_aborts COMMAND vbrun --selftest)
set_tests_properties(unreachable_aborts PROPERTIES WILL_FAIL TRUE)

# Running the guest. THUNRTMAIN calls GlobalHandle, the stub reports it and
# returns AX=0, and the runtime takes its failure branch out through INT 21h
# AH=4Ch. That is correct behaviour for an unimplemented memory manager, and
# pinning it means a regression in the lift, the image or the purge table shows
# up as a DIFFERENT trace rather than passing quietly.
add_test(NAME guest_reaches_globalhandle
         COMMAND vbrun "${CMAKE_SOURCE_DIR}/work/mem_image.bin")
# PASS_REGULAR_EXPRESSION already ignores the exit code, so no WILL_FAIL here --
# the guest exits non-zero on purpose (INT 21h AH=4Ch) and that is the pass.
set_tests_properties(guest_reaches_globalhandle PROPERTIES
    PASS_REGULAR_EXPRESSION "unimplemented: KERNEL.GLOBALHANDLE")
