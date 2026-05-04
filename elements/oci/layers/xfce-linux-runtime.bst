kind: compose
description: XFCE Linux unified runtime

build-depends:
  - oci/layers/xfce-linux-stack.bst

config:
  exclude:
    - devel
    - debug
    - static-blocklist
