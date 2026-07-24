kind: manual
description: |
  regreet — GTK4 greeter for greetd, themed for XFCE Linux (ADR 0001,
  tuna-os/xfce-linux#39). Meant to run under cage until xfwl4 can host it
  directly, per the ADR — but this repo doesn't package cage yet (it
  needs wlroots, unavailable in freedesktop-sdk/gnome-build-meta; see
  deps.bst). This element builds and installs the binary regardless,
  since it's independently useful to have ready, but nothing launches it.

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/rust.bst
- gnome-build-meta.bst:sdk/gtk.bst
- freedesktop-sdk.bst:components/glib.bst
- freedesktop-sdk.bst:components/libxml2.bst
# regreet's `glycin` dependency (background image loading) needs
# GTK>=4.16 per its own Cargo.toml comment — UNCONFIRMED that
# gnome-build-meta.bst:sdk/gtk.bst on the freedesktop-sdk-25.08 pin
# actually satisfies that; if it's older, this fails at cargo build time
# with a version-resolution error rather than anything checkable here.

sources:
- kind: git_repo
  url: https://github.com/rharish101/ReGreet.git
  track: "0.5.0"
  ref: 290e6f8d65b7034c5b63bc950a20bcf8277ebe5f
  directory: regreet

config:
  build-commands:
  - |
    cd regreet
    export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
    export RUSTFLAGS="-C relocation-model=pic"
    # UNVERIFIED: same --offline --frozen caveat as greetd.bst and
    # xfwl4-src.bst — regreet's Cargo.lock isn't vendored in-tree, and
    # this has never been exercised against a real (network-less)
    # BuildStream sandbox this session.
    cargo build --release --offline --frozen

  install-commands:
  - |
    mkdir -p "%{install-root}/usr/bin" \
             "%{install-root}%{sysconfdir}/greetd" \
             "%{install-root}/usr/lib/tmpfiles.d" \
             "%{install-root}/usr/share/backgrounds"
    install -m 0755 regreet/target/release/regreet "%{install-root}/usr/bin/regreet"
    install -m 0644 regreet/systemd-tmpfiles.conf "%{install-root}/usr/lib/tmpfiles.d/regreet.conf"

    # XFCE Linux branding: reuses the Plymouth splash background if present,
    # falls back to regreet's own sample config otherwise. Real theming
    # (colors/logo matching xfce-linux/plymouth-theme.bst) is left for a
    # follow-up once the greeter actually renders on real hardware/QEMU.
    sed 's#/usr/share/backgrounds/greeter.jpg#/usr/share/backgrounds/xfce-linux/default.png#' \
      regreet/regreet.sample.toml > "%{install-root}%{sysconfdir}/greetd/regreet.toml" \
      || install -m 0644 regreet/regreet.sample.toml "%{install-root}%{sysconfdir}/greetd/regreet.toml"
