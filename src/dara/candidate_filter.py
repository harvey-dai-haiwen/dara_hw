"""Candidate CIF filtering by element constraints."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

TOKEN_RE = re.compile(r"[A-Z][a-z]?|[()&|]")
ELEMENT_RE = re.compile(r"[A-Z][a-z]?")


class StructureDatabaseLike(Protocol):
    def get_cifs_by_chemsys(
        self,
        chemsys: str | list[str] | set[str],
        e_hull_filter: float = 0.1,
        copy_files: bool = True,
        dest_dir: str = "dara_cifs",
        exclude_gases: bool = True,
    ): ...


@dataclass(frozen=True)
class FilteredCifSelection:
    selected_paths: list[Path]
    rejected_counts: dict[str, int]
    selected_metadata: list[dict[str, Any]]


def normalize_elements(values: Iterable[str] | None) -> tuple[str, ...]:
    if not values:
        return ()

    elements: list[str] = []
    for value in values:
        for part in re.split(r"[\s,]+", value.strip()):
            if not part:
                continue
            if not ELEMENT_RE.fullmatch(part):
                raise ValueError(f"Invalid element symbol: {part}")
            if part not in elements:
                elements.append(part)
    return tuple(elements)


def _combine_or(
    left: Callable[[set[str]], bool],
    right: Callable[[set[str]], bool],
) -> Callable[[set[str]], bool]:
    def evaluator(elements: set[str]) -> bool:
        return left(elements) or right(elements)

    return evaluator


def _combine_and(
    left: Callable[[set[str]], bool],
    right: Callable[[set[str]], bool],
) -> Callable[[set[str]], bool]:
    def evaluator(elements: set[str]) -> bool:
        return left(elements) and right(elements)

    return evaluator


@dataclass
class ElementExpression:
    text: str | None = None
    elements: set[str] = field(init=False, default_factory=set)

    def __post_init__(self) -> None:
        self.text = (self.text or "").strip()
        self._evaluator: Callable[[set[str]], bool] | None = None
        self._tokens: list[str] = []
        self._index = 0
        if not self.text:
            return

        compact_text = self.text.replace(" ", "")
        self._tokens = TOKEN_RE.findall(compact_text)
        if "".join(self._tokens) != compact_text:
            raise ValueError(f"Invalid element expression: {self.text}")
        self._evaluator = self._parse_expr()
        if self._index != len(self._tokens):
            raise ValueError(f"Unexpected token in element expression: {self._tokens[self._index]}")

    def evaluate(self, elements: set[str]) -> bool:
        if self._evaluator is None:
            return True
        return self._evaluator(elements)

    def _peek(self) -> str | None:
        if self._index >= len(self._tokens):
            return None
        return self._tokens[self._index]

    def _take(self) -> str:
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _parse_expr(self) -> Callable[[set[str]], bool]:
        node = self._parse_term()
        while self._peek() == "|":
            self._take()
            node = _combine_or(node, self._parse_term())
        return node

    def _parse_term(self) -> Callable[[set[str]], bool]:
        node = self._parse_factor()
        while self._peek() == "&":
            self._take()
            node = _combine_and(node, self._parse_factor())
        return node

    def _parse_factor(self) -> Callable[[set[str]], bool]:
        token = self._peek()
        if token is None:
            raise ValueError("Unexpected end of element expression")
        if token == "(":
            self._take()
            node = self._parse_expr()
            if self._peek() != ")":
                raise ValueError("Missing ')' in element expression")
            self._take()
            return node
        if ELEMENT_RE.fullmatch(token):
            self._take()
            self.elements.add(token)
            return lambda elements, token=token: token in elements
        raise ValueError(f"Unexpected token in element expression: {token}")


@dataclass(frozen=True)
class CandidateElementFilter:
    """Three-group element filter for candidate CIF selection."""

    must_elements: Iterable[str] | None = None
    any_elements: Iterable[str] | None = None
    possible_elements: Iterable[str] | None = None
    any_expression: str | None = None

    def __post_init__(self) -> None:
        must = set(normalize_elements(self.must_elements))
        direct_any = set(normalize_elements(self.any_elements))
        possible = set(normalize_elements(self.possible_elements))
        expression = ElementExpression(self.any_expression)
        any_group = direct_any | expression.elements

        overlaps = {
            "must/any": must & any_group,
            "must/possible": must & possible,
            "any/possible": any_group & possible,
        }
        bad = {name: sorted(values) for name, values in overlaps.items() if values}
        if bad:
            raise ValueError(f"Elements may appear in only one filter group: {bad}")

        object.__setattr__(self, "must_elements", tuple(sorted(must)))
        object.__setattr__(self, "any_elements", tuple(sorted(direct_any)))
        object.__setattr__(self, "possible_elements", tuple(sorted(possible)))
        object.__setattr__(self, "_any_expression", expression)

    @property
    def must_set(self) -> set[str]:
        return set(self.must_elements or ())

    @property
    def any_set(self) -> set[str]:
        return set(self.any_elements or ())

    @property
    def possible_set(self) -> set[str]:
        return set(self.possible_elements or ())

    @property
    def any_expression_model(self) -> ElementExpression:
        return self._any_expression

    @property
    def any_group_elements(self) -> set[str]:
        return self.any_set | self.any_expression_model.elements

    @property
    def query_elements(self) -> set[str]:
        return self.must_set | self.any_group_elements | self.possible_set

    def matches(self, elements: Iterable[str]) -> bool:
        return self.rejection_reason(elements) is None

    def rejection_reason(self, elements: Iterable[str]) -> str | None:
        element_set = set(elements)
        if self.must_set and not self.must_set <= element_set:
            return "missing_must"

        any_ok = False
        if self.any_group_elements:
            if self.any_set:
                any_ok = bool(self.any_set & element_set)
            if self.any_expression_model.text:
                any_ok = any_ok or self.any_expression_model.evaluate(element_set)
        if self.any_group_elements and not any_ok:
            return "failed_any"

        if self.query_elements and not element_set <= self.query_elements:
            return "outside_allowed"
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "must": sorted(self.must_set),
            "any": sorted(self.any_set),
            "any_expression": self.any_expression_model.text,
            "possible": sorted(self.possible_set),
            "query_elements": sorted(self.query_elements),
        }


def cif_elements(path: Path | str) -> set[str]:
    from pymatgen.core import Structure

    structure = Structure.from_file(path)
    return {str(element) for element in structure.composition.element_composition.elements}


def filter_cif_paths(paths: Iterable[Path | str], element_filter: CandidateElementFilter) -> FilteredCifSelection:
    selected: list[Path] = []
    selected_metadata: list[dict[str, Any]] = []
    rejected_counts = {"parse_error": 0, "missing_must": 0, "failed_any": 0, "outside_allowed": 0}

    for raw_path in paths:
        path = Path(raw_path)
        try:
            elements = cif_elements(path)
        except Exception:
            rejected_counts["parse_error"] += 1
            continue

        reason = element_filter.rejection_reason(elements)
        if reason is not None:
            rejected_counts[reason] += 1
            continue

        selected.append(path)
        selected_metadata.append({"path": path.as_posix(), "elements": sorted(elements)})

    return FilteredCifSelection(
        selected_paths=selected,
        rejected_counts=rejected_counts,
        selected_metadata=selected_metadata,
    )


def collect_database_cifs(
    databases: Iterable[StructureDatabaseLike],
    element_filter: CandidateElementFilter,
    dest_dir: Path | str,
    e_hull_filter: float = 0.1,
    exclude_gases: bool = True,
) -> list[Path]:
    query_elements = element_filter.query_elements
    if not query_elements:
        raise ValueError("Cannot collect database CIFs without at least one query element.")

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for database in databases:
        before = {path.resolve() for path in dest.glob("*.cif")}
        database.get_cifs_by_chemsys(
            query_elements,
            e_hull_filter=e_hull_filter,
            copy_files=True,
            dest_dir=dest.as_posix(),
            exclude_gases=exclude_gases,
        )
        after = {path.resolve() for path in dest.glob("*.cif")}
        copied.extend(sorted(after - before))
    return copied


def copy_selected_cifs(paths: Iterable[Path | str], dest_dir: Path | str) -> list[Path]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    seen_names: dict[str, int] = {}
    for raw_path in paths:
        path = Path(raw_path)
        count = seen_names.get(path.name, 0)
        seen_names[path.name] = count + 1
        dest_name = path.name if count == 0 else f"{path.stem}_{count}{path.suffix}"
        copied_path = dest / dest_name
        shutil.copy2(path, copied_path)
        copied.append(copied_path)
    return copied
