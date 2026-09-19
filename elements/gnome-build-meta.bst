kind: junction

sources:
- kind: git_repo
  url: gnome:gnome-build-meta.git
  track: gnome-50
  ref: 50.4-0-g8524013485013dd5616bfff02dbeab274d5a4553

config:
  overrides:
    # This along with the patches is required and has to match what gnome-build-meta is using
    freedesktop-sdk.bst: freedesktop-sdk.bst

    # Replace the element so the OCI image has XFCE instead of GNOME apps
    core/meta-gnome-core-apps.bst: core/meta-xfce-core-apps.bst

    # TODO: os-release is handled by gnome-build-meta; skip custom override for now
    # oci/integration/os-release.bst: oci/os-release.bst

    plugins/buildstream-plugins.bst: plugins/buildstream-plugins.bst
    plugins/buildstream-plugins-community.bst: plugins/buildstream-plugins-community.bst
