from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from source_policy import factual_origins


def test_wiki_summary_and_original_are_one_factual_origin():
    original = {'id': 'S1', 'type': 'official', 'url': 'https://example.com/guide'}
    summary = {'id': 'S2', 'type': 'official', 'wiki_path': 'wiki/pages/sources/guide.md', 'origin': original['url'], 'origin_type': 'official'}
    inspiration = {'id': 'S3', 'type': 'secondary', 'purpose': 'structure', 'url': 'https://example.org/style'}
    assert factual_origins([original, summary, inspiration]) == [original]


def test_wiki_summary_cannot_claim_independent_status():
    with pytest.raises(ValueError, match='inherit'):
        factual_origins([{'type': 'independent', 'origin_type': 'official', 'wiki_path': 'wiki/page.md', 'origin': 'https://example.com'}])


def test_wiki_summary_needs_original_provenance():
    with pytest.raises(ValueError, match='origin'):
        factual_origins([{'type': 'official', 'wiki_path': 'wiki/page.md'}])


def test_existing_pattern_reference_stays_excluded():
    source = {'url': 'https://example.com/fact', 'type': 'official'}
    assert factual_origins([source, {'url': 'https://example.com/pattern'}], 'https://example.com/pattern') == [source]
