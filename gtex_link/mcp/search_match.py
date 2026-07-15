"""Query tokenization, identifier match ranking, and symbol->GENCODE resolution.

GTEx's geneSearch endpoint matches a gene_id only (symbol / GENCODE / Ensembl);
there is no description/free-text search and no local corpus. So NL recall is
identifier-based: tokenize, query per candidate token, union, rank by how the
identifier matched. Tokenizer ported from ../genereviews-link/.../retrieval/lexical.py.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from gtex_link.mcp.envelope import McpToolError
from gtex_link.models import GeneRequest
from gtex_link.models.gtex import (
    DEFAULT_GENCODE_VERSION,
    gencode_version_for_dataset,
)

__all__ = [
    "DEFAULT_GENCODE_VERSION",
    "classify_match",
    "gencode_version_for_dataset",
    "recall_terms",
    "resolve_gene_ids",
]

if TYPE_CHECKING:
    from gtex_link.services.gtex_service import GTExService

_TOKEN_RE = re.compile(r"[A-Za-z0-9.]+")
_VERSIONED_GENCODE_RE = re.compile(r"^ENSG\d+\.\d+$", re.IGNORECASE)

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "in",
        "is",
        "it",
        "to",
        "for",
        "on",
        "at",
        "be",
        "as",
        "by",
        "do",
        "up",
        "if",
        "no",
        "so",
        "we",
        "are",
        "was",
        "not",
        "but",
        "has",
        "had",
        "its",
        "can",
        "may",
        "who",
        "how",
        "all",
        "one",
        "two",
        "level",
        "levels",
    }
)

# Maximum candidate tokens turned into upstream geneSearch calls. The upstream
# token-bucket is 5 req/s; a small cap keeps NL search fast.
MAX_QUERY_TOKENS = 5


def _is_gene_shaped(raw: str) -> bool:
    """True if *raw* (original case) looks like a gene identifier, not an English word.

    A gene symbol carries a digit (SCN1A, TP53, HNF1B) or is written in canonical
    all-caps (UMOD, BRCA). English prose words are lowercase and digit-free. This
    lets a real symbol appearing late in a clinical sentence out-rank the stop-word-
    like tokens ('met', 'six') that would otherwise fill the query-token budget and
    evict it (issue #76 D2/D6).
    """
    has_alpha = any(c.isalpha() for c in raw)
    return has_alpha and (any(c.isdigit() for c in raw) or (raw.isupper() and len(raw) >= 2))


def recall_terms(query: str) -> list[str]:
    """Distinct 3+-char lowercased tokens from *query*, excluding stop words.

    Gene-shaped tokens (see :func:`_is_gene_shaped`) are ordered FIRST, otherwise
    the original position is preserved (a stable sort). Callers cap the list at
    ``MAX_QUERY_TOKENS``; ordering gene-shaped tokens first ensures the gene the
    user actually named is never dropped by that cap.
    """
    ordered: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    position = 0
    for match in _TOKEN_RE.finditer(query):
        raw = match.group(0)
        tok = raw.lower()
        if len(tok) < 3 or tok in _STOP_WORDS or tok in seen:
            continue
        seen.add(tok)
        ordered.append((0 if _is_gene_shaped(raw) else 1, position, tok))
        position += 1
    ordered.sort(key=lambda item: (item[0], item[1]))
    return [tok for _priority, _pos, tok in ordered]


def classify_match(token: str, *, symbol: str, gencode_id: str) -> str:
    """Rank how *token* matched an identifier: exact_symbol > exact_ensembl_id > prefix > substring."""
    tok = token.lower()
    sym = symbol.lower()
    ensembl = gencode_id.split(".")[0].lower()
    if tok == sym:
        return "exact_symbol"
    if tok == ensembl or tok == gencode_id.lower():
        return "exact_ensembl_id"
    if sym.startswith(tok) or ensembl.startswith(tok):
        return "prefix"
    return "substring"


_RANK_ORDER = {"exact_symbol": 0, "exact_ensembl_id": 1, "prefix": 2, "substring": 3}


def is_versioned_gencode(value: str) -> bool:
    """True if *value* is already a versioned GENCODE id (no resolution needed)."""
    return bool(_VERSIONED_GENCODE_RE.match(value))


def _unversioned(value: str) -> str:
    """Strip a trailing GENCODE version suffix (ENSG...19 -> ENSG...)."""
    return value.split(".")[0] if is_versioned_gencode(value) else value


async def resolve_gene_ids(
    service: GTExService,
    raw_ids: list[str],
    *,
    gencode_version: str | None = None,
) -> list[str]:
    """Resolve symbols / ids to GENCODE ids for *gencode_version*'s release.

    ``gencode_version`` is the release the caller's dataset uses (see
    ``gencode_version_for_dataset``); ``None`` means the upstream default (v26).
    Versioned ids matching the default release pass through untouched. For any
    other release the version suffix is stripped and re-resolved via get_genes so
    a v26 id (e.g. ENSG00000008710.19) becomes the dataset's id (.20) instead of
    silently returning zero expression rows. Raises McpToolError (invalid_input)
    listing any token that cannot be resolved -- never returns a shorter list.
    """
    target = gencode_version or DEFAULT_GENCODE_VERSION
    if target == DEFAULT_GENCODE_VERSION and all(is_versioned_gencode(rid) for rid in raw_ids):
        return raw_ids

    query_ids = [_unversioned(rid) for rid in raw_ids]
    payload: dict[str, object] = {
        "geneId": query_ids,
        "page": 0,
        "itemsPerPage": len(query_ids),
    }
    if gencode_version is not None:
        payload["gencodeVersion"] = gencode_version
    request = GeneRequest.model_validate(payload)
    result = await service.get_genes(request)
    by_input: dict[str, str] = {}
    for gene in result.data:
        by_input[gene.gene_symbol.lower()] = gene.gencode_id
        by_input[gene.gencode_id.lower()] = gene.gencode_id
        by_input[gene.gencode_id.split(".")[0].lower()] = gene.gencode_id

    resolved: list[str] = []
    unresolved: list[str] = []
    for rid in raw_ids:
        match = by_input.get(rid.lower()) or by_input.get(_unversioned(rid).lower())
        if match is not None:
            resolved.append(match)
        else:
            unresolved.append(rid)
    if unresolved:
        raise McpToolError(
            error_code="invalid_input",
            message=(
                f"Could not resolve to GENCODE IDs: {', '.join(unresolved)}. "
                "Provide a gene symbol (e.g. UMOD) or a versioned GENCODE ID "
                "(e.g. ENSG00000169344.15)."
            ),
        )
    return resolved
