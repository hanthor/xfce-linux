# XFCE Linux Wayland Boot Test - BUG REPORT

**Test Date:** May 13, 2026  
**Status:** 🔴 **FAILED - Critical xfwl4 Segmentation Fault**

## Summary

The XFCE Linux OCI image boots successfully, but **XFCE Wayland session fails with a segmentation fault in the xfwl4 compositor**. The system cannot reach a working XFCE Wayland desktop environment.

## What Works ✅

- ✅ OCI image builds successfully (7.45 GB)
- ✅ System boots to multi-user target
- ✅ GDM display manager starts
- ✅ Network configured correctly
- ✅ SSH accessible (once fully booted)
- ✅ Session files present and correct:
  - `/usr/share/wayland-sessions/xfce-wayland.desktop`
  - `/usr/share/xsessions/xfce-wayland.desktop`
  - `/sbin/startxfce4-wayland` binary present
- ✅ GDM config correctly set to use xfce-wayland session

## What Fails 🔴

### Primary Issue: xfwl4 Compositor Crash

**Error:** Segmentation Fault (exit code 139)

**Symptoms:**
```bash
su - xfce -c 'startxfce4-wayland 2>&1'
-su: line 1:  4389 Segmentation fault         (core dumped) startxfce4-wayland
```

**Kernel dmesg output:**
```
xfwl4[793]: segfault at 8 ip 00007f3e7b17b809 sp 00007ffe766f41e0 error 4
xfwl4[2078]: segfault at 8 ip 00007fddace1b809 sp 00007ffe3a045300 error 4
xfwl4[3396]: segfault at 8 ip 00007f366ff67809 sp 00007ffe4a628420 error 4
xfwl4[4207]: segfault at 8 ip 00007f2142139809 sp 00007ffcaf4e22c0 error 4
```

**Pattern:** Multiple crashes consistently at same instruction pointer, indicating a systematic bug in xfwl4 binary.

## Root Cause Analysis

The xfwl4 binary appears to have a **memory corruption or uninitialized pointer bug** that causes it to crash when trying to initialize Wayland display server.

The crash happens at the same relative address every time:
- Instruction pointer offset: `0x7f3e7b17b809` (varies per run but same relative)
- Memory error: `error 4` (user-space read)
- Likely accessing uninitialized or invalid memory

## Impact

**Current State:**
- ❌ Cannot start XFCE Wayland session
- ❌ Cannot reach graphical desktop
- ❌ System boots to shell only

**Workarounds Attempted:**
1. Manual session start: ❌ Crashes immediately
2. GDM auto-login: ❌ Falls back to GNOME session (not XFCE)
3. Systemd user session: ❌ Crashes with xfwl4

## Required Fixes

### Immediate Actions:
1. **Rebuild xfwl4 binary** with debugging symbols
2. **Fix memory corruption bug** in xfwl4 initialization code
3. **Verify Wayland protocol implementation** in xfwl4
4. **Check library dependencies** (may be ABI mismatches)

### Debugging Steps:
```bash
# Run with GDB to get backtrace
gdb /sbin/startxfce4-wayland
# Run under valgrind to detect memory errors
valgrind --leak-check=full /sbin/startxfce4-wayland
# Check xfwl4 binary dependencies
ldd /usr/bin/xfwl4
# Check for missing symbol exports
nm -D /usr/lib64/libxfce4wl.so.0 | grep init
```

## Configuration Confirmed as Correct

✅ `/etc/gdm/custom.conf`:
```ini
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=xfce
DefaultSession=xfce-wayland

[debug]
Enable=true
```

✅ `/var/lib/AccountsService/users/xfce`:
```ini
[User]
Session=xfce-wayland
XSession=xfce-wayland
```

✅ Session files have correct Exec line:
```ini
Exec=startxfce4-wayland
```

## Next Steps

The **xfwl4 Wayland compositor implementation has a critical bug that must be fixed** before XFCE Wayland can work. This appears to be:

1. A bug in the xfwl4 source code (uninitialized variables, buffer overflow, etc.)
2. An ABI incompatibility between xfwl4 and system libraries
3. A missing dependency or library symbol

**Recommendation:** Focus on debugging and fixing the xfwl4 binary rather than changing configuration - the configuration is correct.

## Test Environment

- **VM:** QEMU with KVM acceleration
- **CPU:** 4 cores
- **RAM:** 8 GB
- **Boot:** UEFI (OVMF)
- **Kernel:** Linux (from freedesktop-sdk)
- **Display:** VNC (127.0.0.1:5901)

