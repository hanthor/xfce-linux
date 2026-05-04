#
#  Copyright (C) 2016, 2019 Codethink Limited
#  Copyright (C) 2018 Bloomberg Finance LP
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Thomas Coldrick <thomas.coldrick@codethink.co.uk>
"""
BuildElement implementation for Bazel builds. This plugin should be
sufficiently powerful to build any Bazel project, provided it is
combined with sources to fetch any external Bazel dependencies.

This plugin really just provides a nice way to run Bazel, with overwriteable
variables you can use to add options. Some sensible looking defaults have
been set, which can be overridden using specific variables.

Most importantly, you should specify the *target* variable with the Bazel
target you wish to build, e.g. ``//foo:bar``.

**Retrieving sources**

Bazel expects to do all downloads itself, so to use it in BuildStream you need
to provide it with sources in the locations it expects.

The main way to do this is with the `bazel_file`__ source plugin, which stages
a file in a fake Bazel repository cache.

__ ../sources/bazel_file.html

Unfortunately though, there is no way to list all the sources needed by a Bazel
project. You have to manually attempt to build, see if you get an error, add the
file, and repeat until the build succeeds.

In bzlmod projects, one significant source of downloads are the module metadata
files from the registries. You can avoid having to download all of those
separately by downloading an entire registry and then passing it to Bazel with
``--registry``. For example, you can add the `Bazel Central Registry`__ as a
source and then provide it to Bazel with
``--registry=file://%{build-root}/bazel-central-registry``.

__ https://github.com/bazelbuild/bazel-central-registry

.. literalinclude:: ../../../src/buildstream_plugins_community/elements/bazel_build.yaml
     :language: yaml
"""

from buildstream import BuildElement


class BazelElement(BuildElement):

    BST_MIN_VERSION = "2.0"

    def configure_sandbox(self, sandbox):
        super().configure_sandbox(sandbox)

        # We set this to be the output user root for bazel. Perhaps we
        # could just use a tmpdir, but I think this could mean we lose
        # the output between build and install. We also may want this to
        # persist for the cache.
        #
        sandbox.mark_directory("/bazel-home")


def setup():
    return BazelElement
