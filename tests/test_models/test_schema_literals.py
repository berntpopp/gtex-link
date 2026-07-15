"""Drift guards: the MCP-input Literal aliases must match their source StrEnums.

The tool input schemas advertise these closed vocabularies as enums (S4). If an
alias drifts from its StrEnum, the schema would advertise a value the runtime
rejects (or omit one it accepts) -- exactly the schema/runtime mismatch class the
fleet audit flagged. These pins fail the day the two diverge.
"""

from __future__ import annotations

from typing import get_args

from gtex_link.models.gtex import (
    DatasetId,
    DatasetLiteral,
    GencodeVersion,
    GencodeVersionLiteral,
    GenomeBuild,
    GenomeBuildLiteral,
    TissueLiteral,
    TissueSiteDetailId,
)


def test_dataset_literal_matches_enum() -> None:
    assert set(get_args(DatasetLiteral)) == {d.value for d in DatasetId}


def test_gencode_version_literal_matches_enum() -> None:
    assert set(get_args(GencodeVersionLiteral)) == {g.value for g in GencodeVersion}


def test_genome_build_literal_matches_enum() -> None:
    assert set(get_args(GenomeBuildLiteral)) == {b.value for b in GenomeBuild}


def test_tissue_literal_is_the_real_tissues_without_the_all_sentinel() -> None:
    values = set(get_args(TissueLiteral))
    assert values == {t.value for t in TissueSiteDetailId if t.value}
    assert "" not in values  # the all-tissues sentinel is never advertised
