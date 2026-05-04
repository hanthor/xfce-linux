#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Authors:
#        Harry Sarson <harry.sarson@codethink.co.uk>
"""
This source plugin downloads a file and makes it available in a Bazel project by
staging it into a fake repository cache.

The cache path is ``_bst_repository_cache``. You can instruct Bazel to use it
with the ``--repository_cache=_bst_repository_cache`` command line option. This
is done by the `bazel_build <../elements/bazel_build.html>`_ plugin by default.

**Usage:**

.. code:: yaml

   # Specify the bazel_file source kind
   kind: bazel_file

   # Specify the url. Using an alias defined in your project
   # configuration is encouraged. 'bst source track' will update the
   # sha256sum in 'ref' to the downloaded file's sha256sum.
   url: upstream:foo

   # Specify the ref. It's a sha256sum of the file you download.
   ref: 6c9f6f68a131ec6381da82f2bff978083ed7f4f7991d931bfa767b7965ebc94b

   # Specify a set of canonical ids. Some Bazel downloads set canonical ids and
   # Bazel will only use an entry in the repository cache if one of the
   # canonicals ids for that entry has the matches.
   canonical_ids: []

   # Modify the default version guessing pattern
   #
   version-guess-pattern: \'(\\d+)\\.(\\d+)(?:\\.(\\d+))?\'

   # Override the version guessing with an explicit version
   #
   version: 5.9

**Canonical IDs:**

Repository cache entries can have one or more canonical IDs which encode the
parameters used to download that file. Bazel won't read an entry from the cache
unless one of its canonical IDs matches the current fetch attempt.

The default canonical ID Bazel uses for a file is the list of URLs specified in
Bazel concatenated together using a space character to separate each URL (see
`source`_). So for a Bazel snippet that looks like:

.. code:: python

    http_archive(
        name = "...",
        sha256 = "...",
        urls = [
            "https://example2.com/thing1.tgz",
            "https://example1.com/thing2.tgz",
        ],
    )

The canonical_id would be
``"https://example2.com/thing1.tgz https://example1.com/thing2.tgz"``.

The ``canonical_ids`` key is a list since it is possible to associate multiple
canonical IDs with each source, such as when multiple Bazel external
repositories download the same file with different URL lists.

You can stop Bazel checking canonical IDs for ``http_archive`` and similar rules
using ``BAZEL_HTTP_RULES_URLS_AS_DEFAULT_CANONICAL_ID=0``. Without canonical ID
checking Bazel will use files in the repository cache provided they have the
correct checksum.

.. _source: https://github.com/bazelbuild/bazel/blob/6052ad65e4185f19944e5138e9b70f6a4eaf9e76/tools/build_defs/repo/cache.bzl#L71


Reporting `SourceInfo <https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfo>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The bazel_file source reports the full URL of the remote file as the *url*.

Further, the bazel_file source reports the `SourceInfoMedium.REMOTE_FILE
<https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfoMedium.REMOTE_FILE>`_
*medium* and the `SourceVersionType.SHA256
<https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceVersionType.SHA256>`_
*version_type*, for which it reports the sha256 checksum of the remote file content as the *version*.

In order to understand how the ``version-guess-pattern`` works, please refer to the documentation
for `utils.guess_version() <https://docs.buildstream.build/master/buildstream.source.html#buildstream.utils.guess_version>`_

An attempt to guess the version based on the remote filename will be made
for the reporting of the *guess_version*. Control over how the guess is made
or overridden is controlled based on the ``version-guess-pattern`` and ``version``
configuration attributes described above.

"""
from pathlib import Path
from typing import Callable, Any, Type, Dict
import hashlib
import shutil
import json
from buildstream import MappingNode, Source, SourceError
from buildstream.utils import url_directory_name

from ._utils import HTTPFetcher, VersionGuesser, add_alias


REPOSITORY_CACHE_DIRNAME = "_bst_repository_cache"

SUPPORTED_HASHES = {
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
}
LINKED_HASHES = {"sha384", "sha512"}


def file_hash(
    filename: Path, hasher: Callable[[], Any] = hashlib.sha256
) -> str:
    """Calculate the hash of a file

    Args:
       filename: A path to a file on disk
       hasher: A hash constructor

    Returns:
      A checksum string

    Raises:
       OsError: In the case there was an issue opening
                or reading `filename`
    """
    h = hasher()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def stage_help(file, info, dest) -> None:
    """Turns fetched file into a cas directory thing"""
    dest.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(file, dest / "file")

    # Store some info about the dependency in the repository_cache, not
    # required by bazel but makes debugging easier.
    with open(dest / "info.txt", "w", encoding="utf-8") as f:
        json.dump(info, f)

    # To prevent user's umask introducing variability here, explicitly
    # set file modes.
    (dest / "file").chmod(0o644)


class BazelFile(Source):
    # pylint: disable=attribute-defined-outside-init

    BST_MIN_VERSION = "2.0"
    BST_EXPORT_MANIFEST = True

    # Increment when changing the plugin such that these sources need to be
    # re-fetched. Changes to `PLUGIN_VERSION` will change the cache-key.
    PLUGIN_VERSION = 1

    KEYS = [
        "canonical-ids",
        "url",
        "ref",
        "version",
        "version-guess-pattern",
    ] + Source.COMMON_CONFIG_KEYS

    def configure(self, node):
        self.canonical_ids = node.get_str_list("canonical-ids", [])
        self.original_url = node.get_str("url")

        node.validate_keys(self.KEYS)

        self.guesser = VersionGuesser()
        self.guesser.configure(node)

        self.load_ref(node)
        self.mark_download_url(self.original_url)

    def preflight(self) -> None:
        return

    def get_unique_key(self) -> Dict[str, Any]:
        return self.guesser.augment_unique_key(
            {
                "url": self.original_url,
                "canonical-ids": self.canonical_ids,
                "plugin_version": str(self.PLUGIN_VERSION),
                "ref": self.ref,
            }
        )

    def load_ref(self, node: MappingNode) -> None:
        self.ref = node.get_str("ref", None)

        url_dir = url_directory_name(self.original_url)

        self.fetcher = HTTPFetcher(
            self,
            mirror_directory=Path(self.get_mirror_directory()) / url_dir,
            url=self.original_url,
            sha256sum=self.sha256sum(),
            guesser=self.guesser,
        )

    def get_ref(self) -> str:
        return self.ref

    def sha256sum(self) -> str:
        return self.get_ref()

    def set_ref(self, ref, node):
        node["ref"] = ref

        self.load_ref(node)

    def is_cached(self):
        return self.fetcher.is_cached()

    def get_source_fetchers(self):
        return [self.fetcher]

    def export_manifest(self):
        url = self.translate_url(self.original_url)
        manifest = {
            "type": "archive",
            "url": url,
            "canonical-ids": self.canonical_ids,
            "sha256": self.sha256sum(),
        }
        add_alias(manifest, self.original_url)
        return manifest

    def stage(self, directory: str) -> None:

        cas_root = (
            Path(directory) / REPOSITORY_CACHE_DIRNAME / "content_addressable"
        )

        dest = cas_root / "sha256" / self.sha256sum()

        with self.timed_activity(
            "Creating repository cache layout in {}".format(dest)
        ):
            stage_help(self.fetcher.mirror_file, self.export_manifest(), dest)

            # Create canonical id marker files
            for canonical_id in self.canonical_ids:
                btes = canonical_id.encode("utf-8")

                for hash_name, hash_fn in SUPPORTED_HASHES.items():
                    file_name = f"id-{hash_fn(btes).hexdigest()}"

                    # Write the canonical id inside the file, not required by
                    # bazel but makes debugging easier.
                    msg = f"generated by {hash_name} of a canonical id of '{canonical_id}'"

                    with open(dest / file_name, "w", encoding="utf-8") as f:
                        print(msg, file=f)

            try:
                hashes = {
                    hash_name: file_hash(
                        self.fetcher.mirror_file, SUPPORTED_HASHES[hash_name]
                    )
                    for hash_name in LINKED_HASHES
                }
            except OSError as e:
                raise SourceError(
                    "{}: Failed to get a checksum of file '{}': {}".format(
                        self, self.fetcher.mirror_file, e
                    )
                ) from e

            for (hash_name, hash_hex) in hashes.items():

                link_dir = cas_root / hash_name / hash_hex
                link_dir.parent.mkdir(parents=True, exist_ok=True)

                link_dir.symlink_to(Path("../sha256") / self.sha256sum())

                assert link_dir.exists()

    def track(self):
        fetcher = HTTPFetcher(
            self.fetcher.source,
            self.fetcher.mirror_directory,
            self.original_url,
            sha256sum=None,
        )

        sha256sum = fetcher.fetch()

        return sha256sum


def setup() -> Type[Source]:
    return BazelFile
