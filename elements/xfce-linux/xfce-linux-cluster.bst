# XFCE Linux monorepo — full desktop stack from hanthor/xfce-wayland
#
# Stack element combining all XFCE dependencies and components.
# This provides the complete runtime for the XFCE desktop environment.

kind: stack
description: |
  Complete XFCE desktop environment dependencies from the xfce-wayland monorepo.
  Includes xfwl4 compositor, xfce4-panel, xfdesktop, thunar, xfce4-terminal,
  and all supporting libraries and panel plugins.

depends:
  # Core dependencies that everything needs
  - freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
  - freedesktop-sdk.bst:components/gtk3.bst
  - gnome-build-meta.bst:sdk/gtk.bst
  - freedesktop-sdk.bst:components/glib.bst
  
  # Build tools
  - freedesktop-sdk.bst:components/cmake.bst
  - freedesktop-sdk.bst:components/meson.bst
  - freedesktop-sdk.bst:components/ninja.bst
  - freedesktop-sdk.bst:components/pkg-config.bst
  - freedesktop-sdk.bst:components/rust.bst

  # Wayland
  - freedesktop-sdk.bst:components/wayland.bst
  - freedesktop-sdk.bst:components/wayland-protocols.bst
  - freedesktop-sdk.bst:components/pixman.bst
  - freedesktop-sdk.bst:components/libdrm.bst

  # System
  - freedesktop-sdk.bst:components/systemd.bst
  - freedesktop-sdk.bst:components/dbus.bst
  - freedesktop-sdk.bst:components/pipewire.bst
  - freedesktop-sdk.bst:components/alsa-lib.bst

  # Libraries
  - freedesktop-sdk.bst:components/libnotify.bst
  - freedesktop-sdk.bst:components/polkit.bst
  - freedesktop-sdk.bst:components/libexif.bst
  - freedesktop-sdk.bst:components/libsoup.bst
  - freedesktop-sdk.bst:components/json-c.bst
  - freedesktop-sdk.bst:components/iso-codes.bst

  # gnome-build-meta deps
  - gnome-build-meta.bst:core-deps/vte.bst
  - gnome-build-meta.bst:core-deps/upower.bst
  - gnome-build-meta.bst:core-deps/libcanberra.bst
  - gnome-build-meta.bst:sdk/gtksourceview.bst

  # GStreamer
  - freedesktop-sdk.bst:components/gstreamer.bst
  - freedesktop-sdk.bst:components/gstreamer-plugins-base.bst
  - freedesktop-sdk.bst:components/gstreamer-plugins-good.bst
