kind: autotools
description: |
  XFCE development tools (xdt-autogen, macros, and visibility tools).
  Build toolchain for XFCE autotools and meson elements (tuna-os/xfce-linux#158).

build-depends:
- freedesktop-sdk.bst:public-stacks/buildsystem-autotools.bst
- freedesktop-sdk.bst:components/glib.bst
# configure hard-requires xsltproc to build the xdt-csource man page.
- freedesktop-sdk.bst:components/libxslt.bst
# ...and meson on PATH (it checks for the program, not a library).
- freedesktop-sdk.bst:public-stacks/buildsystem-meson.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/glib.bst

sources:
- kind: git_repo
  url: xfce:xfce/xfce4-dev-tools.git
  track: xfce4-dev-tools-*
  ref: xfce4-dev-tools-4.21.2-0-ga94438e6514ba63d7c7a5587100e676711335ec6

config:
  configure-commands:
  - ./autogen.sh
  - ./configure --prefix=/usr
