"""The datasets the docs name must be the datasets the server serves.

The README used to say the server served one dataset (`gtex_v8`) and stamped it
"into every response's provenance `_meta`". Both halves were wrong: the expression
tools take a `dataset_id` argument over three datasets, and `_meta.gtex_release`
is a constant that does not follow it. Each dataset is also annotated against a
different GENCODE release -- the very hazard the README's `## Why` section argues
this server exists to remove -- so the mapping is load-bearing, not decoration.

Sources of truth: `get_server_capabilities` (`datasets`) and
`DATASET_GENCODE_VERSION`. Nothing here is hardcoded.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from gtex_link.mcp.metadata import build_capabilities
from gtex_link.models.gtex import DATASET_GENCODE_VERSION

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DATA_DOC = ROOT / "docs" / "data.md"

# | `gtex_v8` | `v26` | ... |
_DATASET_ROW_RE = re.compile(r"^\|\s*`(gtex_[a-z0-9_]+)`\s*\|\s*`(v\d+)`\s*\|", re.MULTILINE)


def _readme_data_section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index("## Data & provenance")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def test_capabilities_and_gencode_map_agree() -> None:
    """The two in-code sources must themselves describe the same datasets."""
    assert set(build_capabilities()["datasets"]) == set(DATASET_GENCODE_VERSION)


def test_readme_names_every_dataset() -> None:
    section = _readme_data_section()
    named = set(re.findall(r"`(gtex_[a-z0-9_]+)`", section))
    served = set(build_capabilities()["datasets"])

    missing = served - named
    assert not missing, f"datasets the server serves but the README omits: {sorted(missing)}"
    invented = named - served - {"gtex_release"}
    assert not invented, f"README names datasets the server does not serve: {sorted(invented)}"


@pytest.mark.parametrize(("dataset", "gencode"), sorted(DATASET_GENCODE_VERSION.items()))
def test_readme_pairs_each_dataset_with_its_gencode_release(dataset: str, gencode: str) -> None:
    """`gtex_v10` must be shown with `v39`, not with some other release."""
    section = _readme_data_section()
    match = re.search(rf"`{re.escape(dataset)}`[^|]*?`({re.escape(gencode)})`", section)
    assert match, f"README does not pair `{dataset}` with its GENCODE release `{gencode}`"


def test_data_doc_dataset_table_matches_the_code() -> None:
    rows = dict(_DATASET_ROW_RE.findall(DATA_DOC.read_text(encoding="utf-8")))
    assert rows == DATASET_GENCODE_VERSION, (
        "docs/data.md's dataset table has drifted from DATASET_GENCODE_VERSION: "
        f"doc={rows} code={DATASET_GENCODE_VERSION}"
    )


def test_docs_do_not_claim_gtex_release_follows_dataset_id() -> None:
    """`_meta.gtex_release` is a constant. If that ever changes, update the docs.

    Pinning the wart keeps the honest wording in README/data.md honest: today a
    `dataset_id="gtex_v10"` call still reports `gtex_release: "gtex_v8"`.
    """
    from gtex_link.mcp.envelope import McpErrorContext, _provenance_meta

    meta = _provenance_meta(McpErrorContext("get_median_expression_levels", dataset_id="gtex_v10"))
    assert meta["dataset_id"] == "gtex_v10"
    assert meta["gtex_release"] == build_capabilities()["gtex_release"]
