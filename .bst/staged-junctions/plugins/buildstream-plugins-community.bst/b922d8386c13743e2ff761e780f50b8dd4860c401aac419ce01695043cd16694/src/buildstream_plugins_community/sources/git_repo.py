"""
git_repo - plugin for git repo handling
==============================================

**Usage:**

.. code:: yaml

   # Specify the git_repo source kind
   kind: git_repo

   # Specify the repository url, using an alias defined
   # in your project configuration is recommended.
   url: upstream:repo.git

   # Optionally specify a tracking branch or tag, this
   # will be used to update the 'ref' when refreshing the pipeline.
   # Tracking supports Unix shell-style globs, as implemented by Python's
   # fnmatch module,  that can be used to filter wanted tag from repository.
   track: release-*

   # Specify the commit checksum, this must be specified in order
   # to checkout sources and build, but can be automatically
   # updated if the 'track' attribute was specified.
   ref: release-3.0-0-gcad743283c43c776d03ae05578f353f728be62e3

   # Specify tracks to exclude in case there's eg bad tags by upstream
   exclude:
   - release-3.0.1

   # Declare the format of ref after tracking. When tracking branches,
   # fetching will be required if sha1 is not used. If git-describe is
   # given, ref follows output of `git describe`. Regardless of format,
   # `git describe` and `git log -1` are expected to work in the sandbox.
   ref-format: git-describe

   # Modify the default version guessing pattern
   #
   version-guess-pattern: \'(\\d+)\\.(\\d+)(?:\\.(\\d+))?\'

   # Override the version guessing with an explicit version
   #
   version: 5.9


Reporting `SourceInfo <https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfo>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The git_repo source reports the full URL of the git repository as the *url*.

Further, the git_repo source reports the `SourceInfoMedium.GIT
<https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfoMedium.GIT>`_
*medium* and the `SourceVersionType.COMMIT
<https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceVersionType.COMMIT>`_
*version_type*, for which it reports the commit sha as the *version*.

If the ref is found to be in ``git-describe`` format, an attempt to guess the version based on the
git tag portion of the ref will be made for the reporting of the *guess_version*. Control over how
the guess is made or overridden is controlled based on the ``version-guess-pattern`` and ``version``
configuration attributes described above.

In order to understand how the ``version-guess-pattern`` works, please refer to the documentation
for `utils.guess_version() <https://docs.buildstream.build/master/buildstream.source.html#buildstream.utils.guess_version>`_

In the case that a git describe string represents a commit that is beyond the tag portion
of the git describe reference (i.e. the version is not exact), then the number of commits
found beyond the tag will be reported in the ``commit-offset`` field of the *extra_data*.
"""

from buildstream import Source, SourceError

from ._git_utils import (
    GitMirror,
    RefFormat,
    REF_REGEX,
    resolve_ref,
    verify_version,
)
from ._utils import VersionGuesser, add_alias


class GitSource(Source):
    BST_MIN_VERSION = "2.0"
    BST_EXPORT_MANIFEST = True

    def configure(self, node):
        CONFIG_KEYS = [
            "ref",
            "url",
            "track",
            "exclude",
            "ref-format",
            "version",
            "version-guess-pattern",
        ]

        node.validate_keys(Source.COMMON_CONFIG_KEYS + CONFIG_KEYS)
        self.ref = None
        self.load_ref(node)

        self.url = node.get_str("url")
        self.mark_download_url(self.url)

        self.tracking = node.get_str("track", None)
        self.exclude = node.get_str_list("exclude", [])

        self.ref_format = node.get_enum(
            "ref-format", RefFormat, RefFormat.SHA1
        )
        self.guesser = VersionGuesser()
        self.guesser.configure(node)

    def preflight(self):
        verify_version()

    def get_unique_key(self):
        return self.guesser.augment_unique_key({"ref": self.ref, "bugfix": 1})

    # loading and saving refs
    def load_ref(self, node):
        if "ref" not in node:
            return
        ref = node.get_str("ref")
        if REF_REGEX.match(ref) is None:
            raise SourceError(f"ref {ref} is not in the expected format")
        self.ref = ref

    def get_ref(self):
        return self.ref

    def set_ref(self, ref, node):
        self.ref = ref
        node["ref"] = ref

    def is_cached(self):
        mirror = GitMirror(
            self,
            self.url,
            self.ref,
        )
        return mirror.has_ref()

    def track(self):
        if not self.tracking:
            return None
        return resolve_ref(
            self,
            self.url,
            self.tracking,
            self.ref_format,
            self.exclude,
        )

    def get_source_fetchers(self):
        yield GitMirror(
            self,
            self.url,
            self.ref,
            guesser=self.guesser,
        )

    def stage(self, directory):
        mirror = GitMirror(
            self,
            self.url,
            self.ref,
        )
        mirror.stage(directory)

    def init_workspace(self, directory):
        mirror = GitMirror(
            self,
            self.url,
            self.ref,
        )
        mirror.init_workspace(directory)

    def export_manifest(self):
        url = self.translate_url(self.url)
        manifest = {
            "type": "git",
            "url": url,
            "commit": self.ref,
        }
        if self.tracking:
            if self.tracking.startswith("refs/"):
                manifest["refspecs"] = [self.tracking]
            else:
                manifest["refspecs"] = [
                    "refs/heads/" + self.tracking,
                    "refs/tags/" + self.tracking,
                ]

        add_alias(manifest, self.url)
        return manifest


def setup():
    return GitSource
