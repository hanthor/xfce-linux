# XFCE Wayland xfwl4 Crash - Debug Notes

## Current Status
- xfwl4 compositor consistently crashes with segmentation fault
- Crash occurs during dynamic linking/relocation phase
- Stack trace shows: `elf_dynamic_do_Rela → _dl_relocate_object → dl_main`
- This indicates memory corruption or ABI incompatibility during relocation

## Crash Evidence
```
May 13 12:13:10 localhost.localdomain kernel: xfwl4[1547]: segfault at 8 ip 00007f... sp 00007f... error 4
May 13 12:13:10 localhost.localdomain systemd-coredump[...]: Process 1547 (xfwl4) dumped core.
```

## Problem Analysis

The crash occurs **before any Rust code executes** - it's purely a loader/linker issue:

1. **Dynamic Linking Problem**: The relocation happens when ld-linux loads the binary and tries to resolve symbols
2. **Library Mismatch**: One or more dependencies (likely GTK-related) has incompatible ABI or missing symbols
3. **Build Environment Issue**: xfwl4 compiled in build environment may differ from runtime environment

## Failed Fixes Attempted

1. ✗ **Code-level error handling**: Added try/unwrap fixes to xfwl4 Rust code
   - Won't help because crash happens before code executes
   
2. ✗ **Adding GTK dependency**: Added GTK to build dependencies
   - Should help but hasn't resolved crash
   
3. ✗ **Simplifying linker flags**: Removed aggressive RUSTFLAGS
   - Didn't resolve the linking issue

## Root Cause Hypotheses

1. **Library symbol incompatibility**: One of xfce-binaries .so files has incompatible symbols
2. **GLIBC version mismatch**: Binary compiled against different GLIBC than runtime
3. **GTK/GLib ABI break**: GTK dependency has changed ABI between build and runtime
4. **Corrupted relocation entries**: Binary was built with conflicting or corrupt relocation info

## Next Steps to Try

1. **Inspect relocation entries**: Use `readelf -r /usr/bin/xfwl4` in VM to see problematic relocations
2. **Check library versions**: Compare libglycin and other libraries between build and runtime
3. **Try static linking**: Build with fewer runtime dependencies
4. **Use different Smithay version**: Current revision might have ABI issues
5. **Use system GTK**: Instead of xfce-binaries GTK, use FDO SDK GTK

## Key Insight

The problem is **not** in xfwl4 code itself. The xfwl4 code is fine. The problem is:
- Binary was built correctly
- But the runtime environment is missing or has incompatible libraries
- OR the xfce-binaries contains corrupted/mismatched libraries

The fix likely needs to be in the build environment setup, not in xfwl4 code.

## Files to Investigate

- `elements/xfce-linux/xfce-binaries.bst` - May have incompatible libraries
- `xfce-wayland/xfwl4/Cargo.toml` - Dependencies that need runtime versions
- `/usr/lib64/libglycin-2.so.0` - Library mentioned in crash but without build-id
- Dynamic symbol table of xfwl4 binary
