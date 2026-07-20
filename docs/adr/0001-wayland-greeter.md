# ADR 0001: Display manager / greeter for XFCE Wayland

Status: proposed · 2026-07-19

## Context

XFCE Linux runs XFCE on Wayland via the xfwl4 compositor. XFCE's traditional
login stack (LightDM + lightdm-gtk-greeter) is X11-only: LightDM can *start*
Wayland sessions, but the GTK greeter itself renders on X, dragging Xorg into
an otherwise Wayland-only image. Today the image inherits **GDM** from the
gnomeos base and the live ISO autologs in via GDM — functional, but it pulls
GNOME Shell machinery into a "vanilla XFCE" system and looks like GNOME at
the door.

## Options

1. **Keep GDM, brand it** — zero engineering; heaviest footprint
   (gnome-shell as greeter), GNOME lock screen semantics. Fine as interim.
2. **greetd + gtkgreet/regreet under xfwl4/cage** — greetd is a tiny session
   manager; regreet (GTK4) or gtkgreet run under any Wayland compositor
   (cage, or xfwl4 itself once stable). Small, Wayland-native, fully
   themeable to XFCE branding. This is what most wlroots distros ship.
   Effort: packaging + session-config element + PAM config. No upstream-XFCE
   blessing, but nothing about it is XFCE-hostile.
3. **Port lightdm-gtk-greeter to Wayland** — "the official greeter, on
   Wayland" story; requires LightDM's Wayland seat support plus a GTK4/layer-
   shell rewrite of the greeter. Largest effort, upstream coordination with
   xfce/lightdm maintainers; would be a genuine upstream contribution and
   fits the "our own official XFCE greeter" ambition.

## Decision (proposed)

Short term: keep GDM (option 1) — it works and the live ISO depends on its
autologin today.
Target: **option 2 (greetd + regreet)** as the shipped greeter for the
opinionated XFCE layer, branded with XFCE Linux assets.
Long term / upstream track: prototype option 3 with the XFCE project if
there's appetite — it would become the real "official XFCE Wayland greeter".

## Consequences

- A `greetd` element + `regreet` element + session-config change, and the
  live ISO's autologin has to move from GDM custom.conf to greetd's
  `initial_session`.
- GNOME Shell/GDM can then be excluded from the image (size + purity win).
- Revisit when xfwl4 is stable enough to host the greeter itself (kiosk
  mode), removing the cage dependency.
