"""
git-module - some kind of git plugin that needs to be documented
================================================================

**Host dependencies**

  * git

**Usage:**

.. code:: yaml

   # Specify the git_module source kind
   kind: git_module

   #
   # TODO: Here is where you document the configuration of
   #       the git_module source kind
   #

   # Modify the default version guessing pattern
   #
   version-guess-pattern: \'(\\d+)\\.(\\d+)(?:\\.(\\d+))?\'

   # Override the version guessing with an explicit version
   #
   version: 5.9


Reporting `SourceInfo <https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfo>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The git_module source reports the full URL of the git repository as the *url*.

Further, the git_module source reports the `SourceInfoMedium.GIT
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
import os

from buildstream import SourceError

from .git_tag import AbstractGitTagSource, GitTagMirror


class GitModuleSource(AbstractGitTagSource):
    # pylint: disable=attribute-defined-outside-init

    BST_REQUIRES_PREVIOUS_SOURCES_TRACK = True

    def get_extra_unique_key(self):
        key = []

        # Distinguish different submodules that reference the same commit
        if self.path:
            key.append({"path": self.path})
        return key

    def get_extra_config_keys(self):
        return ["path"]

    def extra_configure(self, node):
        ref = node.get_str("ref", None)

        self.path = node.get_str("path", None)
        if os.path.isabs(self.path):
            self.path = os.path.relpath(self.path, "/")
        self.mirror = GitTagMirror(
            self,
            self.path,
            self.original_url,
            ref,
            primary=True,
            full_clone=self.full_clone,
            guesser=self.guesser,
        )

    def track(self, previous_sources_dir):
        # list objects in the parent repo tree to find the commit
        # object that corresponds to the submodule
        _, output = self.check_output(
            [self.host_git, "submodule", "status", self.path],
            fail=f"{self}: Failed to run 'git submodule status {self.path}'",
            cwd=previous_sources_dir,
        )

        fields = output.split()
        commit = fields[0].lstrip("-+")
        if len(commit) != 40:
            raise SourceError(
                f"{self}: Unexpected output from 'git submodule status'"
            )

        return commit

    def get_source_fetchers(self):
        yield self.mirror


def setup():
    return GitModuleSource
