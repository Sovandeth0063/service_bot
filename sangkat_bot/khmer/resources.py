# Vendored from KAI_AI shared/kai_khmer (same author), 2026-11-21. Do not edit here; re-copy instead.
"""
Module: resources.py
Purpose: Locate and read bundled tokenizer resources from the installed package.
Usage: from sangkat_bot.khmer.resources import ResourceLoader
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from importlib import resources as importlib_resources
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from sangkat_bot.khmer.exceptions import TokenizerSetupError

PACKAGE_NAME: Final[str] = "sangkat_bot.khmer"
RESOURCE_DIRECTORY: Final[str] = "resources"

# Logical resource names used by the loader, manifest and tokenizer.
DICTIONARY: Final[str] = "dictionary"
NORMALIZER_RULES: Final[str] = "normalizer_rules"
LEXICAL_SPLITS: Final[str] = "lexical_splits"
MODEL: Final[str] = "model"
MODEL_METADATA: Final[str] = "model_metadata"

FILE_NAMES: Final[Mapping[str, str]] = MappingProxyType(
    {
        DICTIONARY: "khmer_dictionary.txt",
        NORMALIZER_RULES: "normalizer_rules.json",
        LEXICAL_SPLITS: "lexical_splits.txt",
        MODEL: "crf_khmer_base.crfsuite",
        MODEL_METADATA: "model_metadata.json",
    }
)

# Resources that must ship with the package; absence is a setup failure.
REQUIRED_RESOURCES: Final[frozenset[str]] = frozenset(
    {DICTIONARY, NORMALIZER_RULES, MODEL, MODEL_METADATA}
)
# Domain overrides are optional; absence is recorded in the manifest instead.
OPTIONAL_RESOURCES: Final[frozenset[str]] = frozenset({LEXICAL_SPLITS})


class ResourceLoader:
    """Read bundled resources relative to the package, never the working dir."""

    def __init__(
        self,
        package: str = PACKAGE_NAME,
        directory: str = RESOURCE_DIRECTORY,
        root: str | Path | None = None,
    ) -> None:
        """Configure a package-relative loader or an explicit resource dir."""
        self._package = package
        self._directory = directory
        self._root = Path(root) if root is not None else None

    def _filename(self, name: str) -> str:
        """Return the bundled filename for one logical resource name."""
        try:
            return FILE_NAMES[name]
        except KeyError as error:
            raise TokenizerSetupError(f"Unknown tokenizer resource: {name}") from error

    def _resource(self, name: str) -> Any:
        """Return the resource traversable for this install layout."""
        filename = self._filename(name)
        if self._root is not None:
            return self._root / filename
        try:
            package_root = importlib_resources.files(self._package)
        except (ImportError, TypeError) as error:
            raise TokenizerSetupError(
                f"Tokenizer package is not importable: {self._package}"
            ) from error
        # joinpath takes one child on Python 3.9 and 3.10.
        resource = package_root.joinpath(self._directory)
        return resource.joinpath(filename)

    def exists(self, name: str) -> bool:
        """Return whether a resource file is present in the resource set."""
        return bool(self._resource(name).is_file())

    @contextmanager
    def path(self, name: str) -> Iterator[Path]:
        """Yield a filesystem path to a resource, failing when it is missing."""
        resource = self._resource(name)
        if not resource.is_file():
            raise TokenizerSetupError(f"Missing bundled resource '{name}' ({self._filename(name)})")
        with importlib_resources.as_file(resource) as resource_path:
            yield Path(resource_path)

    def read_bytes(self, name: str) -> bytes:
        """Read a resource as bytes for fingerprinting and validation."""
        with self.path(name) as resource_path:
            try:
                return resource_path.read_bytes()
            except OSError as error:
                raise TokenizerSetupError(f"Unable to read bundled resource '{name}'") from error


__all__ = [
    "DICTIONARY",
    "FILE_NAMES",
    "LEXICAL_SPLITS",
    "MODEL",
    "MODEL_METADATA",
    "NORMALIZER_RULES",
    "OPTIONAL_RESOURCES",
    "PACKAGE_NAME",
    "REQUIRED_RESOURCES",
    "RESOURCE_DIRECTORY",
    "ResourceLoader",
]
