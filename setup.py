# -*- coding: utf-8 -*-

### NOTE #################################################################################
# This file has to stay format compatible to Python 2, or pip under Python 2 will
# not be able to detect that OctoPrint requires Python 3 but instead fail with a
# syntax error.
#
# So, no f-strings, no walrus operators, no pyupgrade or codemods.
##########################################################################################

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from distutils.command.build_py import build_py as _build_py

import setuptools  # noqa: F401,E402

try:
    import octoprint_setuptools  # noqa: F401,E402
except ImportError:
    octoprint_setuptools = None

import versioneer  # noqa: F401

# ----------------------------------------------------------------------------------------

# Supported python versions
PYTHON_REQUIRES = ">=3.7, <3.12"

# Requirements for setup.py
SETUP_REQUIRES = []

# Requirements for our application
bundled_plugins = [
    "OctoPrint-FileCheck>=2021.2.23",
    "OctoPrint-FirmwareCheck>=2021.10.11",
    "OctoPrint-PiSupport>=2023.5.24",
]
core_deps = [
    "argon2_cffi>=21.3.0,<22",
    "Babel>=2.12.1,<2.13",  # breaking changes can happen on minor version increases
    "cachelib>=0.10.2,<0.11",
    "Click>=8.1.3,<9",
    "colorlog>=6.7.0,<7",
    "emoji>=2.2.0,<3",
    "feedparser>=6.0.10,<7",
    "filetype>=1.2.0,<2",
    "Flask-Assets>=2.0,<3",
    "Flask-Babel>=3.1.0,<4",
    "Flask-Login>=0.6.2,<0.7",  # breaking changes can happen on minor version increases
    "Flask-Limiter>=3.3.0,<4",
    "flask>=2.2.3,<2.3",  # breaking changes can happen on minor version increases (with deprecation warnings)
    "frozendict>=2.3.7,<3",
    "future>=0.18.3,<1",  # not really needed anymore, but leaving in for py2/3 compat plugins
    "markdown>=3.4.3,<4",
    "netaddr>=0.8,<0.9",  # changelog hints at breaking changes on minor version increases
    "netifaces>=0.11,<1",
    "passlib>=1.7.4,<2",
    "pathvalidate>=2.5.2,<3",
    "pkginfo>=1.9.6,<2",
    "psutil>=5.9.4,<6",
    "pydantic>=1.10.7,<2",
    "pylru>=1.2.1,<2",
    "pyserial>=3.5,<4",
    "PyYAML>=5.4.1,<6",  # no changelog available for version 6, so we're not risking it
    "requests>=2.28.2,<3",
    "sarge==0.1.7.post1",
    "semantic_version>=2.10.0,<3",
    "sentry-sdk>=1.19.1,<2",
    "tornado>=6.2,<7",
    "watchdog>=2.3.1,<3",
    "websocket-client>=1.5.1,<2",
    "werkzeug>=2.2.3,<2.3",  # breaking changes can happen on minor version increases
    "wrapt>=1.15,<1.16",
    "zeroconf==0.39.4",  # final version to include universal wheel, later takes ages to compiles on rpi, piwheels has no wheels for latest either
    "zipstream-ng>=1.5.0,<2.0.0",
]
vendored_deps = [
    "blinker>=1.6.1,<2",  # dependency of flask_principal
    "class-doc>=0.2.6,<0.3",  # dependency of with_attrs_docs
    "regex",  # dependency of awesome-slugify
    "unidecode",  # dependency of awesome-slugify
]
plugin_deps = [
    # "OctoPrint-Setuptools>=1.0.3",  # makes sure plugins can import this on setup.py based install
    "wheel",  # makes sure plugins can be built as wheels in OctoPrint's venv, see #4682
]

INSTALL_REQUIRES = bundled_plugins + core_deps + vendored_deps + plugin_deps

# Additional requirements for optional install options and/or OS-specific dependencies
EXTRA_REQUIRES = {
    # Dependencies for OSX
    ":sys_platform == 'darwin'": [
        "appdirs>=1.4.4,<2",
    ],
    # Dependencies for core development
    "develop": [
        # Testing dependencies
        "ddt",
        "mock>=5.0.1,<6",
        "pytest-doctest-custom>=1.0.0,<2",
        "pytest>=7.3.0,<8",
        # pre-commit
        "pre-commit",
        # profiler
        "pyinstrument",
    ],
    # Dependencies for developing OctoPrint plugins
    "plugins": ["cookiecutter>=2.1.1,<3"],
    # Dependencies for building the documentation
    "docs": [
        "sphinx",
        "sphinxcontrib-httpdomain",
        "sphinxcontrib-mermaid",
        "sphinx_rtd_theme",
        "readthedocs-sphinx-ext",
    ],
}

# ----------------------------------------------------------------------------------------
# Anything below here is just command setup and general setup configuration

here = os.path.abspath(os.path.dirname(__file__))


def read_file_contents(path):
    import io

    with io.open(path, encoding="utf-8") as f:
        return f.read()


def copy_files_build_py_factory(files, baseclass):
    class copy_files_build_py(baseclass):
        files = {}

        def run(self):
            print("RUNNING copy_files_build_py")
            if not self.dry_run:
                import shutil

                for directory, files in self.files.items():
                    target_dir = os.path.join(self.build_lib, directory)
                    self.mkpath(target_dir)

                    for entry in files:
                        if isinstance(entry, tuple):
                            if len(entry) != 2:
                                continue
                            source, dest = entry[0], os.path.join(target_dir, entry[1])
                        else:
                            source = entry
                            dest = os.path.join(target_dir, source)

                        print("Copying {} to {}".format(source, dest))
                        shutil.copy2(source, dest)

            baseclass.run(self)

    return type(copy_files_build_py)(
        copy_files_build_py.__name__, (copy_files_build_py,), {"files": files}
    )


class ScanDepsCommand(setuptools.Command):
    description = "Scan dependencies for updates"
    user_options = []

    PYPI = "https://pypi.org/simple/{package}/"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from collections import namedtuple

        import pkg_resources
        import requests
        from packaging.version import parse as parse_version

        Update = namedtuple("Update", ["name", "spec", "current", "latest"])
        update_lower_bounds = []
        update_bounds = []

        all_requires = list(INSTALL_REQUIRES)
        for value in EXTRA_REQUIRES.values():
            all_requires += value

        for r in all_requires:
            requirement = pkg_resources.Requirement.parse(r)

            resp = requests.get(
                self.PYPI.format(package=requirement.project_name),
                headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            )
            resp.raise_for_status()

            def safe_parse_version(version):
                try:
                    return parse_version(version)
                except ValueError:
                    return None

            data = resp.json()
            versions = list(
                filter(
                    lambda x: x and not x.is_prerelease and not x.is_devrelease,
                    map(lambda x: safe_parse_version(x), data.get("versions", [])),
                )
            )
            if not versions:
                continue

            lower = None
            for spec in requirement.specs:
                if spec[0] == ">=":
                    lower = spec[1]
                    break

            latest = versions[-1]

            update = Update(requirement.project_name, str(requirement), lower, latest)

            if str(latest) not in requirement:
                update_bounds.append(update)
            elif lower and parse_version(lower) < latest:
                update_lower_bounds.append(update)

        def print_update(update):
            print(
                f"{update.spec}: latest {update.latest}, pypi: https://pypi.org/project/{update.name}/"
            )

        print("")
        print("The following dependencies can get their lower bounds updated:")
        print("")
        for update in update_lower_bounds:
            print_update(update)

        print("")
        print("The following dependencies should get looked at for a full update:")
        print("")
        for update in update_bounds:
            print_update(update)


def get_cmdclass():
    # make sure these are always available, even when run by dependabot
    global versioneer, octoprint_setuptools, md_to_html_build_py_factory

    cmdclass = versioneer.get_cmdclass()

    if octoprint_setuptools:
        # add clean command
        cmdclass.update(
            {
                "clean": octoprint_setuptools.CleanCommand.for_options(
                    source_folder="src", eggs=["OctoPrint*.egg-info"]
                )
            }
        )

        # add translation commands
        translation_dir = "translations"
        pot_file = os.path.join(translation_dir, "messages.pot")
        bundled_dir = os.path.join("src", "octoprint", "translations")
        cmdclass.update(
            octoprint_setuptools.get_babel_commandclasses(
                pot_file=pot_file,
                output_dir=translation_dir,
                pack_name_prefix="OctoPrint-i18n-",
                pack_path_prefix="",
                bundled_dir=bundled_dir,
            )
        )

    cmdclass["build_py"] = copy_files_build_py_factory(
        {
            "octoprint/templates/_data": [
                "AUTHORS.md",
                "SUPPORTERS.md",
                "THIRDPARTYLICENSES.md",
            ]
        },
        cmdclass["build_py"] if "build_py" in cmdclass else _build_py,
    )

    cmdclass["scan_deps"] = ScanDepsCommand

    return cmdclass


def package_data_dirs(source, sub_folders):
    dirs = []

    for d in sub_folders:
        folder = os.path.join(source, d)
        if not os.path.exists(folder):
            continue

        for dirname, _, files in os.walk(folder):
            dirname = os.path.relpath(dirname, source)
            for f in files:
                dirs.append(os.path.join(dirname, f))

    return dirs


def params():
    # make sure these are always available, even when run by dependabot
    global versioneer, get_cmdclass, read_file_contents, here, PYTHON_REQUIRES, SETUP_REQUIRES, INSTALL_REQUIRES, EXTRA_REQUIRES

    name = "OctoPrint"
    version = versioneer.get_version()
    cmdclass = get_cmdclass()

    description = "The snappy web interface for your 3D printer"
    long_description = read_file_contents(os.path.join(here, "README.md"))
    long_description_content_type = "text/markdown"

    python_requires = PYTHON_REQUIRES
    setup_requires = SETUP_REQUIRES
    install_requires = INSTALL_REQUIRES
    extras_require = EXTRA_REQUIRES

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: Other Audience",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Natural Language :: English",
        "Natural Language :: German",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: JavaScript",
        "Topic :: Printing",
        "Topic :: System :: Monitoring",
    ]
    author = "Gina Häußge"
    author_email = "gina@octoprint.org"
    url = "https://octoprint.org"
    license = "GNU Affero General Public License v3"
    keywords = "3dprinting 3dprinter 3d-printing 3d-printer octoprint"

    project_urls = {
        "Community Forum": "https://community.octoprint.org",
        "Bug Reports": "https://github.com/OctoPrint/OctoPrint/issues",
        "Source": "https://github.com/OctoPrint/OctoPrint",
        "Funding": "https://support.octoprint.org",
    }

    packages = setuptools.find_packages(where="src")
    package_dir = {
        "": "src",
    }
    package_data = {
        "octoprint": package_data_dirs(
            "src/octoprint", ["static", "templates", "plugins", "translations"]
        )
        + ["util/piptestballoon/setup.py"]
    }

    include_package_data = True
    zip_safe = False

    if os.environ.get("READTHEDOCS", None) == "True":
        # we can't tell read the docs to please perform a pip install -e .[docs], so we help
        # it a bit here by explicitly adding the docs dependencies
        install_requires = install_requires + extras_require["docs"]

    entry_points = {"console_scripts": ["octoprint = octoprint:main"]}

    return locals()


setuptools.setup(**params())
