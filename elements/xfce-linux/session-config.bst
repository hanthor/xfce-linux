# XFCE Linux session configuration
#
# Sets up the xfwl4 Wayland session, default applications,
# and desktop environment settings.

kind: stack
description: |
  XFCE Linux session configuration dependencies.
  Ensures systemd and dbus are available for session management.

depends:
  - freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
  - freedesktop-sdk.bst:components/systemd.bst
  - freedesktop-sdk.bst:components/dbus.bst
