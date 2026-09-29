"""Published research evidence must remain tied to the admitted frozen release."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'experiments/confirmation'


def test_confirmation_mirror_preserves_frozen_release_and_all_data_hashes():
    catalog = json.loads((ROOT / 'data/catalog.json').read_bytes())
    assert catalog['archive_sha256'] == '869e318dd5f328205dd181ee836ef267bd2ae278f6430a9e8ddc661fbc689d03'
    assert catalog['row_count'] == 5184
    assert catalog['overall_registered_gate'] == 'FAILED'
    for name, expected in catalog['files'].items():
        data = (ROOT / name).read_bytes()
        assert len(data) == expected['bytes'], name
        assert hashlib.sha256(data).hexdigest() == expected['sha256'], name
    summary = json.loads((ROOT / 'data/summary.json').read_bytes())
    assert summary['primary']['overall_pass'] is False
    assert summary['primary']['clean_guard_pass'] is False


def test_publication_record_is_source_bound_and_preserves_provider_scope():
    record = json.loads((ROOT / 'publication.json').read_bytes())
    assert record['canonical_repository'] == 'szl-holdings/szl-forge'
    assert record['source_revision'] == '48cb7630dc5c6982cf14755da72d3d07cd45740c'
    assert record['model_inference_performed'] is False
    assert record['hosted_readback']['source_artifact_set_matches'] is True
    assert record['hosted_readback']['public_files'] == 20
    assert record['hosted_readback']['provider_html_metadata_insertion'] is True
    files = record['hosted_readback']['files']
    assert len(files) == 20
    assert len({entry['path'] for entry in files}) == 20
    for entry in files:
        data = (ROOT / entry['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['source_sha256'], entry['path']


if __name__ == '__main__':
    test_confirmation_mirror_preserves_frozen_release_and_all_data_hashes()
    test_publication_record_is_source_bound_and_preserves_provider_scope()
    print('OK: frozen confirmation evidence and canonical publication binding are intact.')
