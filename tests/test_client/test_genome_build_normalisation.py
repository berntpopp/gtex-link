"""GTEx accepts only ``GRCh38/hg38`` / ``GRCh37/hg19`` for ``genomeBuild`` (issue #165).

Bare ``GRCh38``/``GRCh37`` are advertised to callers, so the client must map them
to the upstream vocabulary before sending -- otherwise GTEx answers HTTP 422.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gtex_link.api.client import GTExClient
from tests.conftest import GTEX_BASE

if TYPE_CHECKING:
    import respx

    from gtex_link.config import GTExAPIConfigModel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("given", "sent"),
    [
        ("GRCh38", "GRCh38/hg38"),
        ("GRCh38/hg38", "GRCh38/hg38"),
        ("GRCh37", "GRCh37/hg19"),
        ("GRCh37/hg19", "GRCh37/hg19"),
    ],
)
async def test_genome_build_sent_in_gtex_vocabulary(
    respx_mock: respx.MockRouter, test_api_config: GTExAPIConfigModel, given: str, sent: str
) -> None:
    route = respx_mock.get(f"{GTEX_BASE}/reference/gene").respond(200, json={"data": []})
    client = GTExClient(config=test_api_config)
    await client.get_genes({"geneId": ["BRCA1"], "genomeBuild": given})
    await client.close()
    assert route.calls.last.request.url.params["genomeBuild"] == sent
