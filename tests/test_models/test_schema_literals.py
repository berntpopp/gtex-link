"""Drift guards: the MCP-input Literal aliases must match their source of truth.

The tool input schemas advertise these closed vocabularies as enums (S4). If an
alias drifts, the schema would advertise a value the runtime rejects (or omit one
it accepts) -- exactly the schema/runtime mismatch class the fleet audit flagged.

For the tissue vocabulary the drift ANCHOR is the vendored GTEx OpenAPI spec
(`docs/gtex-openapi-spec-formatted.json`), NOT the `TissueSiteDetailId` StrEnum:
comparing the Literal to the StrEnum would only compare two views of the same
hand-maintained list. The spec is, however, over-inclusive by one LEGACY name --
`Cells_Transformed_fibroblasts` was the pre-v8 label for what v8/v10 now serve as
`Cells_Cultured_fibroblasts`. The LIVE API does not serve the old name:
`GET /dataset/tissueSiteDetail?datasetId=gtex_v8` returns 54 tissues (with
`Cells_Cultured_fibroblasts`, not `Cells_Transformed_fibroblasts`), and every
expression query for it returns empty. Advertising it would make the schema WIDER
than the runtime (the harmful mismatch direction), so the advertised vocabulary is
the spec MINUS the documented deprecations. A NEW real tissue added to the spec
still fails this test until the enum adds it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

from gtex_link.models.gtex import (
    DatasetId,
    DatasetLiteral,
    GencodeVersion,
    GencodeVersionLiteral,
    GenomeBuild,
    GenomeBuildLiteral,
    TissueChoice,
    TissueLiteral,
    TissueSiteDetailId,
)

_SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "gtex-openapi-spec-formatted.json"

# Names present in the spec enum but NOT served by the live v8/v10 API (schema must
# stay a subset of the runtime). Evidence is in the module docstring above.
_SPEC_ONLY_DEPRECATED = {"Cells_Transformed_fibroblasts"}


def _spec_enum(schema_name: str) -> set[str]:
    spec = json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
    return set(spec["components"]["schemas"][schema_name]["enum"])


def _expected_tissues() -> set[str]:
    return _spec_enum("TissueSiteDetailId") - _SPEC_ONLY_DEPRECATED


def test_deprecated_tissue_is_in_the_spec_but_excluded() -> None:
    # Pin the premise of the exclusion: the name IS in the spec (so this is a real
    # correction, not a typo), and it is the only one we drop.
    assert _SPEC_ONLY_DEPRECATED.issubset(_spec_enum("TissueSiteDetailId"))


def test_tissue_vocabulary_matches_the_served_spec_source_of_truth() -> None:
    expected = _expected_tissues()
    # The advertised Literal must be EXACTLY the served vocabulary (no "" sentinel,
    # which the runtime rejects) -- never narrower (a valid tissue would be unusable)
    # nor wider (a schema-valid tissue the runtime rejects).
    assert set(get_args(TissueLiteral)) == expected
    # The StrEnum view used for the median tool's scalar-or-list parameter is the same
    # vocabulary (its deduped $ref form).
    assert {t.value for t in TissueChoice} == expected
    # And the StrEnum (used by ensure_valid_tissue / capabilities) carries every served
    # tissue, plus only the "" all-tissues sentinel on top.
    assert {t.value for t in TissueSiteDetailId} == expected | {""}


def test_dataset_literal_matches_enum() -> None:
    assert set(get_args(DatasetLiteral)) == {d.value for d in DatasetId}


def test_gencode_version_literal_matches_enum() -> None:
    assert set(get_args(GencodeVersionLiteral)) == {g.value for g in GencodeVersion}


def test_genome_build_literal_matches_enum() -> None:
    assert set(get_args(GenomeBuildLiteral)) == {b.value for b in GenomeBuild}
