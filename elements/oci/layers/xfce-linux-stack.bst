kind: stack
description: XFCE Linux stack — freedesktop-sdk base plus XFCE desktop

depends:
  # XFCE Linux dependencies and applications
  - xfce-linux/deps.bst
  # gnome-build-meta gnomeos stack (provides freedesktop-sdk base)
  - gnome-build-meta.bst:oci/gnomeos/stack.bst

public:
  bst:
    integration-commands:
      # Wipe /var (may contain build-time state) and recreate with correct structure
      - rm -rfv /home /root /opt /mnt /srv /var
      - mkdir -p /var/home /var/roothome /var/opt /var/mnt /var/srv /var/tmp
      - ln -s var/home /home
      - ln -s var/roothome /root
      - ln -s var/opt /opt
      - ln -s var/mnt /mnt
      - ln -s var/srv /srv
