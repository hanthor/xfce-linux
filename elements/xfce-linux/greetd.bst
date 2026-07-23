kind: manual
description: |
  greetd — minimal, flexible login manager daemon. Session-manager half of
  the greetd + regreet Wayland greeter stack (ADR 0001, tuna-os/xfce-linux#39).

  Built but NOT activated by this element: greetd.service is installed
  disabled, and GDM remains the active display manager (xfce-linux-stack.bst
  unchanged). Switching the live ISO / default session over to greetd is a
  separate follow-up, once this survives the LUKS e2e's login-path assertions
  per the issue's own phased plan.

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/rust.bst
- freedesktop-sdk.bst:components/linux-pam.bst
- freedesktop-sdk.bst:components/linux-pam-base.bst
- freedesktop-sdk.bst:components/systemd.bst

sources:
- kind: git_repo
  url: https://git.sr.ht/~kennylevinsen/greetd
  track: "0.9.0"
  ref: f3f32498851c6775a9d9ca0d46239b9a6de78204
  directory: greetd

config:
  build-commands:
  - |
    cd greetd
    export PKG_CONFIG_PATH="/usr/lib64/pkgconfig:/usr/lib/pkgconfig:/usr/share/pkgconfig"
    export RUSTFLAGS="-C relocation-model=pic"
    # UNVERIFIED: greetd's Cargo.lock isn't vendored in-tree (no vendor/ dir,
    # no .cargo/config.toml at the pinned ref — checked directly against the
    # upstream repo). This --offline --frozen invocation mirrors xfwl4-src.bst's
    # existing pattern in this repo, but that pattern's own success has never
    # been confirmed by a completed build either (the multi-runner pipeline
    # hasn't finished an x86_64 build this session, let alone reached this
    # element). If this fails on crate resolution, a cargo-sources vendoring
    # element needs to land ahead of this one — see tuna-os/xfce-linux#39.
    cargo build --release --offline --frozen --workspace --exclude fakegreet

  install-commands:
  - |
    mkdir -p "%{install-root}/usr/bin" \
             "%{install-root}/usr/lib/systemd/system" \
             "%{install-root}/usr/lib/sysusers.d" \
             "%{install-root}%{sysconfdir}/greetd" \
             "%{install-root}%{sysconfdir}/pam.d"

    cat > "%{install-root}/usr/lib/sysusers.d/greetd.conf" <<'EOF'
    u greeter - "greetd greeter" /var/lib/greetd -
    m greeter video
    EOF
    install -m 0755 greetd/target/release/greetd "%{install-root}/usr/bin/greetd"
    install -m 0755 greetd/target/release/agreety "%{install-root}/usr/bin/agreety"
    install -m 0644 greetd/greetd.service "%{install-root}/usr/lib/systemd/system/greetd.service"

    # NOT FUNCTIONAL YET: this launches regreet under `cage`, which this
    # repo doesn't package (cage needs wlroots, unavailable in
    # freedesktop-sdk or gnome-build-meta — see deps.bst's comment). Kept
    # as the intended config rather than something bogus, since greetd.service
    # ships disabled and nothing exercises this file yet — but don't expect
    # it to actually start a session until a compositor is sorted out.
    cat > "%{install-root}%{sysconfdir}/greetd/config.toml" <<'EOF'
    [terminal]
    vt = 1

    [default_session]
    command = "cage -s -- /usr/bin/regreet"
    user = "greeter"

    [initial_session]
    command = "cage -s -- /usr/bin/regreet"
    user = "greeter"
    EOF

    # PAM stack: mirrors sddm.bst's rewrite target in this org's images —
    # freedesktop-sdk/gnomeos ships `system-auth` as the shared include,
    # not upstream sddm's own `system-local-login`/`system-login` names
    # (confirmed for tromso; UNCONFIRMED specifically for xfce-linux, which
    # has no other pam.d/* element to cross-check against yet).
    cat > "%{install-root}%{sysconfdir}/pam.d/greetd" <<'EOF'
    auth     include system-auth
    account  include system-auth
    password include system-auth
    session  include system-auth
    EOF
