# Derived from gnome-build-meta.bst 50~ core/meta-gnome-core-apps.bst
# Overridden to replace GNOME core apps with XFCE equivalents.

kind: stack
description: |
  Overridden to ship XFCE desktop stack instead of GNOME core apps.

depends:
  # XFCE desktop stack (xfwl4 compositor, panel, session, etc.)
  - xfce-linux/xfce-linux-cluster.bst

  # Keep some freedesktop utilities
  - gnome-build-meta.bst:core/baobab.bst
  - gnome-build-meta.bst:core/gnome-disk-utility.bst
