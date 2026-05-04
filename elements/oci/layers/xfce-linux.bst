kind: compose
description: XFCE Linux final layer

build-depends:
  - freedesktop-sdk.bst:components/gcc.bst
  - oci/layers/xfce-linux-runtime.bst

config:
  exclude:
    - debug
    - extra
    - static-blocklist
