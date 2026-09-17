# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[SemVer](https://semver.org/).

## [Unreleased]

### Added
- Triage of `EMPIRE.EXE` establishing it as Visual Basic 3 p-code, not x86:
  one imported module (`VBRUN300`), 14 relocations across 114 KB, and a nine
  byte entry point that hands control to `VBRUN300.100` (THUNRTMAIN).
- `tools/lift_vbrun.py`, which lifts all 99 `VBRUN300.DLL` code segments to C
  through the stock pcrecomp NE pipeline with no project-specific lifter.
- `tools/build.py`, a parallel bring-up compile loop that buckets diagnostics.
- `runtime/main.c`, a host that maps the flat image, builds the selector table
  and calls THUNRTMAIN.
- `CMakeLists.txt` with two ctest cases: an unlifted target must abort rather
  than return, and the guest must reach `KERNEL.GlobalHandle`.

### Fixed
- Upstream, in pcrecomp: `decode16.decode_one` raising on a truncated
  instruction, a stale BCD override in `ne_lift.py` emitting `_v / 0` for
  `aam 0`, and a wrong PASCAL purge for `USER.TrackPopupMenu` (14, but it takes
  seven arguments, so 16).

### Notes
- Nothing generated is committed. `work/` holds the entire lifted tree and the
  memory image, and is gitignored; both regenerate from a local copy of the
  binary in one command each.
