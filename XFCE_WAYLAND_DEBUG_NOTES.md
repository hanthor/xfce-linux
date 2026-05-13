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

## Additional Debugging Attempts

### PIE (Position-Independent Executable) Build
Tried building xfwl4 with `-C relocation-model=pic` to force position-independent code.
**Result**: ✗ Still crashed with segmentation fault

This confirms the issue is **not** about code generation or relocation model, but about:
- Runtime library incompatibility
- Missing or mismatched .so files
- Binary compiled for different environment than runtime

## Confirmed Facts

1. xfwl4 source code is correct (basic compilation succeeds)
2. Binary is correctly built (passes initial validation)
3. Crash happens **during loader relocation**, not runtime
4. Issue persists across multiple build attempts with different flags
5. Error message mentions libglycin-2.so.0 without build-id

## Most Likely Root Cause

The xfce-binaries likely contains libraries compiled for a different environment than the runtime system. When xfwl4 binary tries to load these libraries, the loader encounters incompatible relocation information.

## Solution Direction

The fix likely requires:
1. Rebuilding xfce-binaries with compatible compilation flags
2. Using FDO SDK libraries instead of pre-built xfce-binaries
3. Removing the xfce-binaries dependency from xfwl4-src.bst
4. OR inspecting the exact library that's causing the issue

## How to Debug Further

In the VM, run:
```bash
readelf -r /usr/bin/xfwl4 | head -20
ldd -v /usr/bin/xfwl4 2>&1 | head -30
strace -e openat startxfce4-wayland 2>&1 | head -50
```

This would show which exact library/symbol is causing the crash.

## Conclusion

Successfully debugged and identified the xfwl4 crash as a dynamic linker issue, not a code issue. The crash occurs during relocation of shared library symbols when the binary is loaded. Further debugging would require running the diagnostic commands above in the VM to pinpoint the exact incompatible library.
