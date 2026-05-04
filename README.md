# XFCE Linux — Wayland-Native XFCE Desktop Image

A bootable, immutable OS image built with [BuildStream](https://buildstream.build/) using the [freedesktop-sdk](https://freedesktop-sdk.pages.freedesktop.org/) as the base. Ships the complete XFCE desktop environment with the [xfwl4](https://github.com/hanthor/xfce-wayland/xfwl4) Wayland compositor.

## Architecture

```
xfce-linux/
├── Justfile              # Build/test/test commands
├── project.conf          # BuildStream project configuration
├── bst-dashboard.py      # Live build dashboard
├── elements/
│   ├── freedesktop-sdk.bst      # Junction to freedesktop-sdk
│   ├── gnome-build-meta.bst     # Junction to gnome-build-meta
│   ├── plugins/                 # BuildStream plugins
│   ├── xfce-linux/
│   │   ├── deps.bst             # XFCE stack dependency stack
│   │   ├── xfce-linux-cluster.bst  # Full monorepo build
│   │   └── session-config.bst   # Session files, dconf, defaults
│   ├── core/
│   │   └── meta-xfce-core-apps.bst  # Core app override (no GNOME)
│   └── oci/
│       ├── xfce-linux.bst       # Final OCI image
│       ├── os-release.bst       # os-release file
│       └── layers/
│           ├── xfce-linux.bst         # Final compose layer
│           ├── xfce-linux-runtime.bst # Runtime compose (no devel)
│           └── xfce-linux-stack.bst   # Full stack definition
├── files/
│   ├── dconf/               # dconf database settings
│   ├── fakecap/             # Fake xattr capability injection
│   └── plymouth/            # Boot splash
├── include/
│   └── aliases.yml          # Source URL aliases
└── patches/
    └── freedesktop-sdk/     # freedesktop-sdk patches
```

## Quick Start

### Build the OCI image

```bash
# Build with BuildStream (runs inside bst2 container)
just build

# Or build in background with live dashboard
just bst-build
just dashboard  # http://localhost:8765
```

### Boot in a VM

```bash
# Generate bootable disk image and boot in QEMU
just show-me-the-future

# Or step by step:
just generate-bootable-image
just boot-vm

# Fast ephemeral VM (no disk, boots via virtiofs)
just boot-fast
```

### Development

```bash
# Run any bst command
just bst show oci/xfce-linux.bst
just bst info xfce-linux/xfce-linux-cluster.bst

# Clean build artifacts
just clean

# Lint the image
just lint
```

## Components

| Component | Description |
|-----------|-------------|
| **xfwl4** | Native Wayland compositor (Rust/Smithay) |
| **xfce4-panel** | XFCE panel with 31 plugins |
| **xfdesktop** | Desktop manager (wallpaper, icons) |
| **thunar** | File manager (Wayland via -Dx11=disabled) |
| **xfce4-terminal** | Terminal emulator (gtk-layer-shell) |
| **xfce4-session** | Session manager |
| **xfce4-settings** | Settings manager |
| **xfce4-notifyd** | Notification daemon |
| **xfce4-power-manager** | Power management |
| **mousepad** | Text editor |
| **ristretto** | Image viewer |
| **catfish** | File search |
| **tumbler** | Thumbnailer |
| **garcon** | Menu system |
| **xfconf** | Configuration daemon |

## Build Infrastructure

- **BuildStream 2** — Declarative build system with remote caching
- **freedesktop-sdk** — Base SDK with ~2000 packages
- **gnome-build-meta** — Build infrastructure (plugins, aliases)
- **bootc** — Bootable container image format
- **podman** — Container runtime for build/test
- **bcvk** — Fast ephemeral VM testing

## Cache

BuildStream uses remote caches to avoid rebuilding everything:
- `https://gbm.gnome.org:11003` — GNOME Build Machine
- `https://cache.projectbluefin.io:11001` — Project Bluefin

## Known Issues

- First build downloads ~50GB of sources/artifacts
- freedesktop-sdk junction requires network access
- bcvk requires `cargo` for auto-install

## References

- [xfwl4 compositor](https://github.com/hanthor/xfce-wayland)
- [freedesktop-sdk](https://freedesktop-sdk.pages.freedesktop.org/)
- [BuildStream](https://buildstream.build/)
- [bootc](https://containers.github.io/bootc/)
- [gnome-build-meta](https://gitlab.gnome.org/GNOME/gnome-build-meta)
- [Project Bluefin / dakota](https://github.com/projectbluefin/dakota)
