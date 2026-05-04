"""
go_module - plugin for handling dependencies in go projects
===========================================================s

**Usage:**

.. code:: yaml

   # Specify the go_module source kind
   kind: go_module

   # Specify the repository url, using an alias defined
   # in your project configuration is recommended.
   url: upstream:repo.git

   # Set the module name
   module: golang.org/x/xerrors


Reporting `SourceInfo <https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfo>`_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The go_module source reports the full URL of the git repository as the *url*.

Further, the go_module source reports the `SourceInfoMedium.GIT
<https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceInfoMedium.GIT>`_
*medium* and the `SourceVersionType.COMMIT
<https://docs.buildstream.build/master/buildstream.source.html#buildstream.source.SourceVersionType.COMMIT>`_
*version_type*, for which it reports the commit sha as the *version*.

Given that the go_module stores references using git-describe format, an attempt to guess the version based
on the git tag portion of the ref will be made for the reporting of the *guess_version*.

In the case that a git describe string represents a commit that is beyond the tag portion
of the git describe reference (i.e. the version is not exact), then the number of commits
found beyond the tag will be reported in the ``commit-offset`` field of the *extra_data*.
"""

import os
import posixpath
import re
from html.parser import HTMLParser

from buildstream import Source, SourceError, utils
import requests

from ._utils import VersionGuesser
from ._git_utils import (
    GitMirror,
    RefFormat,
    REF_REGEX,
    resolve_ref,
    get_full_sha,
    verify_version,
)

# A go version https://go.dev/ref/mod#versions
# Examples: v0.0.0, v1.12.134, v8.0.5-pre, and v2.0.9+meta
VERSION_REGEX = re.compile(r"((v\d+)\.\d+\.\d+(?:-[a-z]+)?)(\+[a-z]+)?")

# A go pseudo-version https://go.dev/ref/mod#pseudo-versions
# Example: v0.0.0-20191109021931-daa7c04131f5
PSEUDO_VERSION_REGEX = re.compile(
    r"(v\d+)\.\d+\.\d+-(?:[a-z]+\.)?(?:0\.)?(?:\d+)-([a-z0-9]+)"
)


class GoImportParser(HTMLParser):
    def __init__(self):
        self._repo_path = ""
        self._vcs = ""
        self._url = ""
        super().__init__()

    def handle_starttag(self, tag: str, attrs: tuple[str]) -> None:
        if tag != "meta":
            return
        attr_dict = dict((k, v) for k, v in attrs)
        if attr_dict.get("name") == "go-import":
            self.base_module, self.vcs, self.url = attr_dict["content"].split()


def get_module_subdirectory(module):
    # special case for github: a github repository can only have two components
    if module.startswith("github.com"):
        parts = module.split("/")
        return "/".join(parts[3:])

    response = requests.get(f"https://{module}?go-get=1", timeout=10)

    parser = GoImportParser()
    parser.feed(response.text)

    if parser.base_module is None:
        return ""

    base_module = parser.base_module

    if module.startswith(base_module):
        return module.removeprefix(base_module).removeprefix("/")

    return ""


def extract_go_directive(directory):
    """
    Extracts the go directive from a module directory. This needs to be included
    in the modules.txt to allow use of new go features.

    See https://go.dev/ref/mod#go-mod-file-go
    """
    go_mod_filename = os.path.join(directory, "go.mod")
    if not os.path.exists(go_mod_filename):
        return None

    with open(go_mod_filename, encoding="utf-8") as f:
        go_mod = f.read()

    for l in go_mod.splitlines():
        if l.startswith("go "):
            return l

    return None


class GoModuleSource(Source):
    BST_MIN_VERSION = "2.0"

    BST_REQUIRES_PREVIOUS_SOURCES_TRACK = True
    BST_REQUIRES_PREVIOUS_SOURCES_STAGE = True
    BST_EXPORT_MANIFEST = True

    def configure(self, node):
        CONFIG_KEYS = ["ref", "url", "module"]

        node.validate_keys(Source.COMMON_CONFIG_KEYS + CONFIG_KEYS)
        self.ref = None
        self.load_ref(node)

        self.url = node.get_str("url")
        self.module = node.get_str("module")
        self.mark_download_url(self.url)

        # Because of how we are tracking references, it seems to be pointless
        # to expose ``version-guess-pattern`` or ``version`` parameters, so
        # we just use a default VersionGuesser which reports appropriate
        # versions for the git-describe type versions.
        self.guesser = VersionGuesser()

    def preflight(self):
        verify_version()

    def get_unique_key(self):
        return {"ref": self.ref, "module": self.module, "bugfix": 1}

    # loading and saving refs
    def load_ref(self, node):
        if "ref" not in node:
            return
        ref = node.get_mapping("ref")
        ref.validate_keys(
            ["go-version", "git-ref", "explicit", "subdirectory"]
        )
        self.ref = {
            "go-version": ref.get_str("go-version"),
            "git-ref": ref.get_str("git-ref"),
            "explicit": ref.get_bool("explicit"),
        }
        if "subdirectory" in ref:
            self.ref["subdirectory"] = ref.get_str("subdirectory")
        if REF_REGEX.match(self.ref["git-ref"]) is None:
            raise SourceError(f"ref {ref} is not in the expected format")

    def get_ref(self):
        return self.ref

    def set_ref(self, ref, node):
        self.ref = ref
        node["ref"] = ref

    def is_cached(self):
        mirror = GitMirror(
            self,
            self.url,
            self.ref["git-ref"],
        )
        return mirror.has_ref()

    def track(self, previous_sources_dir):
        go_sum = os.path.join(previous_sources_dir, "go.sum")
        go_mod = os.path.join(previous_sources_dir, "go.mod")
        with open(go_mod, encoding="utf-8") as file:
            explicit = self.module in file.read()
        with open(go_sum, encoding="utf-8") as file:
            go_sum_contents = file.read()

        for line in go_sum_contents.splitlines():
            # Third item is checksum which we ignore
            module, version, _ = line.split()
            if version.endswith("/go.sum"):
                # We ignore these for now
                continue
            if version.endswith("/go.mod"):
                # We ignore these for now
                continue

            if module == self.module:
                break
        else:
            raise SourceError(f"go.mod did not contain {self.module}")

        subdirectory = get_module_subdirectory(self.module)
        m = PSEUDO_VERSION_REGEX.fullmatch(version)
        if m:
            # Special-case, this encodes git commit
            _, short_sha = m.groups()
            resolved = get_full_sha(self, self.url, short_sha)
        else:
            m = VERSION_REGEX.fullmatch(version)
            if not m:
                raise SourceError(f"version string {version} not recognized")
            clean_version, major_version, _ = m.groups()

            # The actual module files may or may not be in a major version subdirectory.
            # We drop the version here, and we handle it when staging.
            subdirectory = subdirectory.removesuffix(
                major_version
            ).removesuffix("/")

            lookup = posixpath.join(subdirectory, clean_version)

            resolved = resolve_ref(
                self,
                self.url,
                lookup,
                RefFormat.GIT_DESCRIBE,
                (),
            )
        ref = {
            "go-version": version,
            "git-ref": resolved,
            "explicit": explicit,
        }
        if subdirectory:
            ref["subdirectory"] = subdirectory

        return ref

    def get_source_fetchers(self):
        yield GitMirror(
            self,
            self.url,
            self.ref["git-ref"],
            guesser=self.guesser,
        )

    def stage(self, directory):
        vendor_directory = os.path.join(directory, "vendor", self.module)
        os.makedirs(vendor_directory, exist_ok=True)
        mirror = GitMirror(
            self,
            self.url,
            self.ref["git-ref"],
            stage_objects=False,
        )

        # We stage the whole repository into a temporary directory, then we
        # extract the module (which could be in a subdirectory) to the actual
        # staging directory
        with self.tempdir() as temp:
            mirror.stage(temp)
            module_dir = temp

            if "subdirectory" in self.ref:
                module_dir = os.path.join(temp, self.ref["subdirectory"])

            m = VERSION_REGEX.fullmatch(self.ref["go-version"])
            if m:
                _, major_version, _ = m.groups()
                version_dir = os.path.join(module_dir, major_version)

                if int(major_version[1:]) >= 2 and os.path.exists(version_dir):
                    module_dir = version_dir
                else:
                    self.debug(
                        f"Module {self.module}, major version {major_version} "
                        "does not have a version subdirectory"
                    )

            # This uses hardlinks (or copy files) so is safe to use
            # on temporary files.
            utils.link_files(module_dir, vendor_directory)

        go_directive = extract_go_directive(vendor_directory)
        self._append_modules_txt(directory, go_directive)

    def _append_modules_txt(self, directory, go_version):
        """
        Append this module to the vendor/modules.txt file. The file format is not documented,
        so this function tries to mimic what go itself does.
        """
        vendor_dir = os.path.join(directory, "vendor")
        modules_txt = os.path.join(vendor_dir, "modules.txt")
        module_dir = os.path.join(vendor_dir, self.module)

        with open(modules_txt, "a", encoding="utf-8") as file:
            if self.ref["explicit"]:
                print(f"# {self.module} {self.ref['go-version']}", file=file)
                if go_version:
                    print(f"## explicit; {go_version}", file=file)
                else:
                    print("## explicit", file=file)
            else:
                print(f"# {self.module}", file=file)

            for path, dirs, files in os.walk(module_dir):
                # Skip .git directories for now, eventually we want to stop staging them altogether
                if ".git" in dirs:
                    dirs.remove(".git")
                # os.walk() is not guaranteed to return elements in a deterministic order
                dirs.sort()
                if "go.mod" in files or any(f.endswith(".go") for f in files):
                    print(os.path.relpath(path, vendor_dir), file=file)

    def export_manifest(self):
        url = self.translate_url(
            self.url,
            alias_override=None,
            primary=False,
        )
        return {
            "type": "git",
            "url": url,
            "commit": self.ref["git-ref"],
        }


def setup():
    return GoModuleSource
