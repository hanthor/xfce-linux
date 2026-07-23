kind: meson
description: |
  cage — kiosk Wayland compositor that hosts a single application
  fullscreen. Used to host regreet (ADR 0001, tuna-os/xfce-linux#39) until
  xfwl4 is stable enough to host the greeter itself.

  UNCONFIRMED: cage v0.3.1 requires wlroots-0.20 via pkg-config
  (meson.build: `dependency('wlroots-0.20', ...)`). No element in this repo
  currently provides wlroots — xfwl4 is Smithay/Rust-based, not wlroots, so
  nothing else needed it. This element assumes
  `freedesktop-sdk.bst:components/wlroots.bst` exists and satisfies that
  exact version pin; neither has been checked against the actual
  freedesktop-sdk-25.08 manifest. If it's missing or version-mismatched,
  this element fails at configure time before any C code even compiles.

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-meson.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/wlroots.bst
- freedesktop-sdk.bst:components/wayland.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst
- freedesktop-sdk.bst:components/libseat.bst
- freedesktop-sdk.bst:components/libinput.bst
- freedesktop-sdk.bst:components/libdrm.bst
- freedesktop-sdk.bst:components/pixman.bst
- freedesktop-sdk.bst:components/dummy-gbm.bst

sources:
- kind: git_repo
  url: https://github.com/cage-kiosk/cage.git
  track: v0.3.1
  ref: b7b774ac957b6d8c7b39f0dcb9ebe19de3e8a45d

variables:
  meson-local: >-
    -Dman-pages=disabled
