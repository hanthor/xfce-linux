# Copyright (c) 2018 freedesktop-sdk
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors:
#        Valentin David <valentin.david@gmail.com>
#        Adam Jones <adam.jones@codethink.co.uk>
"""
A buildstream element plugin used to produce a manifest file containing
useful informations about its dependencies. By default, this manifest
is formatted similar to a `flatpak-builder manifest`_ but it can also
be an `SPDX 2.3`_ SBoM instead.

.. _flatpak-builder manifest: https://docs.flatpak.org/en/latest/module-sources.html
.. _SPDX 2.3: https://spdx.dev/

The manifest contains useful information, such as:
    - CPE data, such as CVE patches
    - Package name
    - Version
    - Sources
    - Source locations
    - SHAs
    - Patch files

The manifest file is exported as a JSON file to the path provided under
the ``path`` configuration option in the .bst file.

Output format
=============

By default, the plugin outputs a JSON file inspired by the Flatpak
manifest format. Here are examples of the outputs:

.. code-block:: JSON

    {
       "type": "git",
       "url": "https://foo.bar/repo.git",
       "commit": "hash/git-describe"
    }

.. code-block:: JSON

    {
       "type": "archive",
       "url": "https://path/to/package.tgz",
       "sha256": "checksum"
    }

.. code-block:: JSON

    {
       "type": "patch",
       "path": "path/to/patches"
    }

The plugin also allows generating SPDX version 2.3, in JSON format, by
setting the ``output-type: spdx`` configuration option. In that case,
you can also set the ``spdx-info`` configuration option to a dictionary
containing the following keys: ``name``, ``creators``, ``created``,
``data-license`` and ``doc-namespace``. These map directly to the
equivalent fields from the SPDX document creation information section,
with the following caveat:

* ``creator`` is a list of string, the user is responsible for
  formatting it according to the SPDX specification.
* ``created`` is a UNIX timestamp, which gets converted to the format
  mandated by SPDX.

Please note that this information is mandatory for the output to be
valid SPDX, but the plugin allows leaving them unset in case you want
to set them in post-processing. This is particularly useful for
``created``.


Source provenance data
======================

By default, this plugin tries to use the `Source Provenance API`_ introduced
in BuildStream 2.5. This is now the recommended way to extract source
information from dependencies. Source Provenance API can be disabled by setting
``use-source-provenance`` to ``false``. This can be useful if your project needs to
keep compatibility with older BuildStream version.

When ``use-source-provenance`` is set to ``false``, the plugin falls back to the
export_manifest protocol, if implemented by the source plugin, or to hard-coded
support for a few plugins. Source plugins can implement the export_manifest
protocol by setting ``BST_EXPORT_MANIFEST`` to ``True`` and implementing the
``export_manifest()`` method. Please note that the ``export_manifest`` protocol
is deprecated and support for it will be removed when dropping support for
BuildStream versions older than 2.5.

.. _Source Provenance API: https://docs.buildstream.build/master/buildstream.source.html#generating-sourceinfo-for-provenance-information

CPE Data
========

Dependency elements can manually declare CPE data in their public
section. For example:

.. code:: yaml

   public:
     cpe:
       product: gnutls
       vendor: gnu
       version: '1.0'

This data will be set in the ``x-cpe`` field of the entry.

If not present, ``product`` will be automatically be inferred from the
name of the element.

When using the `Source Provenance API`_, version guessing is handled as
explained in the BuildStream documentation. Otherwise, this plugin implements
its own version guessing from commit for git and from basename of URL for
archives. See below for details.

Version guessing
****************

The default version regular expression is ``\\d+\\.\\d+(?:\\.\\d+)?`` (2 or 3
numerical components separated by dots). It is possible to change the version
regular expression with public data field ``version-match`` under the ``cpe``
domain. Please note that this only applies when not using Source Provenance
API.

The version regular expression must follow Python regular expression
syntax.  A version regular expression with no group will match exactly
the version. A version regular expression with groups will match
components of the version with each groups. The components will then
be concatenated using ``.`` (dot) as a separator.

``version-match`` in the ``cpe`` public data will never be exported in
the ``x-cpe`` field of the manifest.

Here is an example of ``version-match`` where the filename is
``openssl1_1_1d.tar.gz``, the result version will be ``1.1.1d``.

.. code:: yaml

   public:
     cpe:
       version-match: '(\\d+)_(\\d+)_(\\d+[a-z]?)'
"""

import os
import re
import json
import posixpath

from datetime import datetime, timezone
from enum import Enum

from buildstream import Element, Node, ElementError
from buildstream.utils import get_bst_version

try:
    from buildstream import SourceInfo, SourceInfoMedium, SourceVersionType
except ImportError:
    pass


class CollectManifestElement(Element):
    BST_MIN_VERSION = "2.0"
    BST_ARTIFACT_VERSION = 2

    BST_FORBID_RDEPENDS = True
    BST_FORBID_SOURCES = True
    BST_RUN_COMMANDS = False
    BST_STRICT_REBUILD = True

    def configure(self, node):
        self.path = node.get_str("path", None)
        self.output_type = node.get_enum(
            "output-type", OutputType, OutputType.MANIFEST
        )

        spdx_info = node.get_mapping("spdx-info", {})
        spdx_info.validate_keys(
            ["creators", "created", "data-license", "doc-namespace", "name"]
        )
        self.spdx_creators = spdx_info.get_str_list("creators", None)
        self.spdx_created_timestamp = spdx_info.get_int("created", None)
        self.spdx_data_license = spdx_info.get_str("data-license", None)
        self.spdx_doc_namespace = spdx_info.get_str("doc-namespace", None)
        self.spdx_name = spdx_info.get_str("name", None)

        self.source_provenance = node.get_bool("use-source-provenance", True)

        if self.source_provenance and get_bst_version() < (2, 5):
            raise ElementError(
                "Source provenance API is only available with buildstream 2.5 or later."
            )

    def preflight(self):
        pass

    def get_unique_key(self):
        key = {"path": self.path}

        if self.output_type == OutputType.SPDX:
            key["output_type"] = self.output_type.value
            key["spdx_info"] = (
                self.spdx_creators,
                self.spdx_data_license,
                self.spdx_created_timestamp,
                self.spdx_doc_namespace,
                self.spdx_name,
            )

        if self.source_provenance:
            key["source_provenance"] = True

        return key

    def configure_sandbox(self, sandbox):
        pass

    def stage(self, sandbox):
        pass

    def extract_cpe(self, dep):
        cpe = dep.get_public_data("cpe")

        if cpe is None:
            cpe = {}
        else:
            cpe = cpe.strip_node_info()

        if "product" not in cpe:
            cpe["product"] = os.path.basename(os.path.splitext(dep.name)[0])

        sources = list(dep.sources())

        # Keep compatibility with versions previous to source API.
        # This still looks for "version-match" in the public:cpe fields
        version_match = cpe.pop("version-match", None)
        if "version" not in cpe and sources:
            matcher = VersionMatcher(version_match)
            version = matcher.get_version(sources)

            if version is None:
                if version_match is None:
                    self.warn("Missing version to {}.".format(dep.name))
                else:
                    fmt = '{}: {}: version match string "{}" did not match anything.'
                    msg = fmt.format(self.name, dep, version_match)
                    raise ElementError(msg)

            if version:
                cpe["version"] = version

        return cpe

    def extract_sources(self, dep):
        sources = list(dep.sources())

        source_infos = []
        source_locations = []

        if self.source_provenance:
            for source in sources:
                infos = source.collect_source_info()
                if infos is not None:
                    source_infos.extend(infos)
            source_locations = convert_source_locations(self, source_infos)
        else:
            infos = get_source_locations(sources)
            source_locations.extend(infos)

        return source_infos, source_locations

    def get_dependencies(self, dep, visited):
        if dep in visited:
            return
        visited.add(dep)
        for subdep in dep.dependencies(recurse=False):
            yield from self.get_dependencies(subdep, visited)
        yield dep

    def assemble(self, sandbox):
        visited = set()
        # Old style manifests. They are always generated to be put in public data
        modules = []
        # New style manifest. They are only available with bst 2.5, and can be
        # disabled in the configuration to keep compatibility with old bst
        # When disabled or otherwise not available, each element is replaced
        # with `None` so as to keep the same number of elements as the `modules`
        # variable above
        element_infos = []

        for top_dep in self.dependencies(recurse=False):
            for dep in self.get_dependencies(top_dep, visited):
                import_manifest = dep.get_public_data("cpe-manifest")
                import_infos = dep.get_public_data("source-info-manifest")

                if import_manifest:
                    import_manifest = import_manifest.strip_node_info()
                    modules.extend(import_manifest["modules"])

                    manifest_len = len(import_manifest["modules"])

                    if self.source_provenance and import_infos:
                        import_infos = import_infos.strip_node_info()

                        assert (
                            len(import_infos["element-infos"]) == manifest_len
                        )
                        element_infos.extend(import_infos["element-infos"])
                    else:
                        if self.source_provenance:
                            self.warn(
                                f'Dependency "{dep.name}" from project "{dep.project_name}"'
                                " doesn't use the source provenance API",
                                warning_token="legacy-manifest",
                            )
                        element_infos.extend([None] * manifest_len)
                else:
                    cpe = self.extract_cpe(dep)
                    infos, sources = self.extract_sources(dep)

                    modules.append(
                        {
                            "name": dep.name,
                            "x-cpe": cpe,
                            "sources": sources,
                        }
                    )
                    if self.source_provenance:
                        element_infos.append(
                            {
                                "name": dep.normal_name,
                                "project-name": dep.project_name,
                                "source-infos": infos,
                            }
                        )
                    else:
                        element_infos.append(None)

        manifest = {
            "//NOTE": (
                "This is a generated manifest from buildstream files "
                "and not usable by flatpak-builder"
            ),
            "modules": modules,
        }

        manifest_node = Node.from_dict(dict(manifest))
        self.set_public_data("cpe-manifest", manifest_node)

        # Serialize source provenance info to put into public data
        if self.source_provenance:
            for elem_info in element_infos:
                if elem_info is None:
                    continue
                source_infos = elem_info["source-infos"]
                if any(isinstance(info, SourceInfo) for info in source_infos):
                    elem_info["source-infos"] = [
                        info.serialize() for info in source_infos
                    ]

            self.set_public_data(
                "source-info-manifest",
                Node.from_dict({"element-infos": element_infos}),
            )

        # Generate SPDX by converting the above manifest
        # Only if requested as an output
        spdx = None
        if self.path and self.output_type == OutputType.SPDX:
            spdx = self.generate_spdx(modules, element_infos)

        if self.path:
            basedir = sandbox.get_virtual_directory()
            dirname = os.path.dirname(self.path)
            filename = os.path.basename(self.path)
            vdir = basedir.open_directory(
                dirname.lstrip(os.path.sep), create=True
            )

            if vdir.exists(filename):
                if filename[-1].isdigit():
                    version = int(filename[-1]) + 1
                    new_filename = list(filename)
                    new_filename[-1] = str(version)
                    filename = "".join(new_filename)
                else:
                    filename = filename + "-1"

            output = spdx if self.output_type == OutputType.SPDX else manifest
            with vdir.open_file(filename, mode="w") as o:
                json.dump(output, o, indent=2)

        return os.path.sep

    def generate_spdx(self, modules, element_infos):
        packages = []
        assert len(modules) == len(element_infos)
        for module, elem_info in zip(modules, element_infos):
            if self.source_provenance and elem_info is not None:
                packages.extend(self.generate_spdx_for_element(elem_info))
            else:
                packages.extend(self.generate_spdx_for_module(module))

        relationships = []
        for package in packages:
            relationships.append(
                {
                    "spdxElementId": "SPDXRef-DOCUMENT",
                    "relationshipType": "DESCRIBES",
                    "relatedSpdxElement": package["SPDXID"],
                }
            )

        def relationship_sort_key(relationship):
            return (
                relationship["spdxElementId"],
                relationship["relatedSpdxElement"],
                relationship["relationshipType"],
            )

        spdx = {
            "SPDXID": "SPDXRef-DOCUMENT",
            "spdxVersion": "SPDX-2.3",
            "packages": sorted(packages, key=lambda pkg: pkg["SPDXID"]),
            "relationships": sorted(relationships, key=relationship_sort_key),
        }

        creation_info = spdx["creationInfo"] = {}

        if self.spdx_creators:
            creation_info["creators"] = self.spdx_creators

        if self.spdx_created_timestamp:
            created_datetime = datetime.fromtimestamp(
                self.spdx_created_timestamp, timezone.utc
            )
            # This is a specific variant of isoformat, that python's datetime
            # module doesn't support
            # https://spdx.github.io/spdx-spec/v2.3/document-creation-information/#691-description
            creation_info["created"] = created_datetime.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        if self.spdx_doc_namespace:
            spdx["documentNamespace"] = self.spdx_doc_namespace

        if self.spdx_data_license:
            spdx["dataLicense"] = self.spdx_data_license

        if self.spdx_name:
            spdx["name"] = self.spdx_name

        return spdx

    def generate_spdx_for_module(self, module):
        """
        Generate SPDX package information from the passed-in module, which is an
        entry from an old style manifest (before the introduction of the source
        provenance API)
        """
        packages = []

        name = module["name"]
        cpe = module["x-cpe"]
        sources = module["sources"]

        for idx, source in enumerate(sources):
            package_name = None
            if "url" in source:
                package_name = extract_package_name(
                    self,
                    {
                        "url": source["url"],
                        "medium": source["type"],
                    },
                )

            if package_name is None:
                package_name = name

            package = {
                "SPDXID": f"SPDXRef-{name.replace('/', '-')}-{idx}",
                "comment": f"Product: {cpe['product']}",
                "filesAnalyzed": False,
                "name": package_name,
            }

            if "url" in source:
                # FIXME: Make `downloadLocation` use SPDX URL format for packages.
                package["downloadLocation"] = source["url"]

            if "version" in cpe:
                package["versionInfo"] = cpe["version"]

            if "type" in source:
                package["sourceInfo"] = source["type"]

            packages.append(package)

        return packages

    def generate_spdx_for_element(self, elem_info):
        """
        Generate SPDX package information from the passed-in module, which is an
        entry from a new style manifest (using the source provenance API)
        """
        packages = []

        name = elem_info["name"]
        project_name = elem_info["project-name"]
        sources = elem_info["source-infos"]

        for idx, source in enumerate(sources):
            package_name = extract_package_name(self, source)
            if not package_name:
                package_name = name

            package = {
                "SPDXID": f"SPDXRef-{project_name}-{name}-{idx}",
                "filesAnalyzed": False,
                "name": package_name,
            }

            package["downloadLocation"] = source["url"]
            if "version-guess" in source:
                package["versionInfo"] = source["version-guess"]
            else:
                package["versionInfo"] = source["version"]

            package["sourceInfo"] = source["kind"]

            packages.append(package)

        return packages


class OutputType(Enum):
    MANIFEST = "manifest"
    SPDX = "spdx"


class VersionMatcher:

    DEFAULT_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")

    def __init__(self, match):
        if match is None:
            self.__match = self.DEFAULT_VERSION_RE
        else:
            self.__match = re.compile(match)

    def _parse_version(self, text):
        m = self.__match.search(text)
        if not m:
            return None
        if self.__match.groups == 0:
            return m.group(0)
        else:
            return ".".join(m.groups())

    def get_version(self, sources):
        """
        This method attempts to extract the source version
        from a dependency. This data can generally be found
        in the url for tar balls, or the ref for git repos.

        :sources A list of BuildStream Sources
        """
        for source in sources:
            export_manifest = getattr(source, "BST_EXPORT_MANIFEST", False)
            if export_manifest:
                manifests = source.export_manifest()
                version = None
                if isinstance(manifests, dict):
                    manifests = [manifests]
                elif not isinstance(manifests, list):
                    raise ElementError(
                        f"Invalid manifest for source {source} of type {type(manifests)}"
                    )
                for manifest in manifests:
                    if manifest["type"] == "git":
                        version = self._parse_version(manifest["commit"])
                    elif manifest["type"] == "archive":
                        version = self._parse_version(
                            posixpath.basename(manifest["url"])
                        )
                    if version is not None:
                        break

                if version is None:
                    continue
                return version
            if source.get_kind() in ["tar", "zip"]:
                url = source.url
                filename = url.rpartition("/")[2]
                version = self._parse_version(filename)
                if version is not None:
                    return version
            elif source.get_kind().startswith("git"):
                ref = source.mirror.ref
                version = self._parse_version(ref)
                if version is not None:
                    return version
        return None


def get_source_locations(sources):
    """
    Returns a list of source URLs and refs, currently for
    git, tar and patch sources.

    :sources A list of BuildStream Sources
    """
    source_locations = []
    for source in sources:
        export_manifest = getattr(source, "BST_EXPORT_MANIFEST", False)
        if export_manifest:
            manifest = source.export_manifest()
            if isinstance(manifest, dict):
                source_locations.append(manifest)
            elif isinstance(manifest, list):
                source_locations.extend(manifest)
            else:
                raise ElementError(
                    f"Invalid manifest for source {source} of type {type(manifest)}"
                )
            continue
        if source.get_kind() in ["git"]:
            url = source.translate_url(
                source.mirror.url,
                alias_override=None,
                primary=source.mirror.primary,
            )
            source_locations.append(
                {
                    "type": source.get_kind(),
                    "url": url,
                    "commit": source.mirror.ref,
                }
            )
        if source.get_kind() in ["patch"]:
            patch = source.path.rpartition("/")[2]
            source_locations.append({"type": source.get_kind(), "path": patch})
        if source.get_kind() in ["tar", "zip"]:
            source_locations.append(
                {"type": "archive", "url": source.url, "sha256": source.ref}
            )

    return source_locations


def convert_source_locations(element, source_infos):
    """
    Returns a list of source information formatted in the same format as
    ``get_source_locations()`` above. For compatibility with older versions of the plugin.

    :source_infos A list of BuildStream SourceInfos
    """
    source_locations = []
    for source_info in source_infos:
        if source_info.medium == SourceInfoMedium.GIT:
            assert source_info.version_type == SourceVersionType.COMMIT
            if (
                source_info.extra_data
                and "tag-name" in source_info.extra_data
                and "commit-offset" in source_info.extra_data
            ):
                commit = "{}-{}-g{}".format(
                    source_info.extra_data["tag-name"],
                    source_info.extra_data["commit-offset"],
                    source_info.version,
                )
            else:
                commit = source_info.version

            source_location = {
                "type": "git",
                "url": source_info.url,
                "commit": commit,
            }
        elif source_info.medium == SourceInfoMedium.LOCAL:
            if source_info.kind in ("patch", "patch_queue"):
                source_location = {"type": "patch", "path": source_info.url}
            else:
                source_location = {"type": "dir", "path": source_info.url}
        elif source_info.medium == SourceInfoMedium.WORKSPACE:
            source_location = {"type": "workspace"}
        elif source_info.medium == SourceInfoMedium.REMOTE_FILE:
            assert source_info.version_type == SourceVersionType.SHA256
            source_location = {
                "type": "archive",
                "url": source_info.url,
                "sha256": source_info.version,
            }
        else:
            element.warn(
                f"Unsupported source info medium {source_info.medium}",
                warning_token="unsupported-source-info",
            )
            source_location = None
        # Create x-cpe field in source location to use the version guesser to
        # get the version for source provenance API.
        # TODO: Move the rest of the x-cpe fields to the source:x-cpe field
        if source_location is not None:
            cpe = {}
            product = extract_package_name(element, source_info.serialize())
            if product is not None:
                cpe["product"] = product

            if source_info.version_guess is not None:
                cpe["version"] = source_info.version_guess

            if cpe:
                source_location["x-cpe"] = cpe

        source_locations.append(source_location)

    return source_locations


def extract_package_name(element, source_info):
    basename = os.path.basename(source_info["url"])

    if (
        "extra-data" in source_info
        and "crate-name" in source_info["extra-data"]
    ):
        return source_info["extra-data"]["crate-name"]

    if source_info["medium"] == "git":
        if basename.endswith(".git"):
            return basename[: -len(".git")]
        return basename
    elif source_info["medium"] in ("remote-file", "archive"):
        stem = re.split(r"\.(tar|tgz|tbz|zip|crate)", basename)[0]
        package = re.split("[-_][0-9]", stem)[0]
        return package
    elif source_info["medium"] == "local" and source_info["kind"].startswith(
        "patch"
    ):
        # FIXME: these should be handled as files rather than packages
        return None
    elif source_info["medium"] == "local":
        return basename
    else:
        element.warn(
            f"Can't extract a package name from source info {source_info}",
            warning_token="unsupported-source-info",
        )
        return None


def setup():
    return CollectManifestElement
