"""Published research evidence must remain tied to the admitted frozen release."""
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import rollout_holographic_proof_v2 as holo
from tools import rollout_proof_flow_shell as flow

ROOT = Path(__file__).resolve().parents[1] / 'experiments/confirmation'
WORKBENCH = 'https://szlholdings-szl-foundation-confirmation.hf.space'


def live_trial_handoff():
    served = (ROOT / 'index.html').read_bytes().decode('utf-8')
    matches = re.findall(r'<aside id="fresh-trials"[^>]*>.*?</aside>', served, flags=re.DOTALL)
    assert len(matches) == 1, 'Declare exactly one off-origin exploratory workbench handoff'
    return matches[0]


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
        path = 'source-index.html' if entry['path'] == 'index.html' else entry['path']
        data = (ROOT / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['source_sha256'], entry['path']
    source = (ROOT / 'source-index.html').read_bytes().decode('utf-8')
    expected = holo.add_before(source, '</head>', '  ' + holo.STYLE + '\n')
    expected = holo.add_before(expected, '</head>', '  ' + flow.STYLE + '\n')
    expected = holo.add_before(expected, '</body>', '  ' + flow.SCRIPT + '\n')
    expected = holo.add_before(expected, '</body>', '  ' + holo.SCRIPT + '\n')
    expected = holo.add_before(expected, '</head>', '  <link rel="stylesheet" href="proof-origin.css" />\n')
    assert expected.count('<body>') == 1
    expected = expected.replace('<body>', '<body class="foundation-confirmation">')
    served = (ROOT / 'index.html').read_bytes()
    assert served.decode('utf-8').replace(live_trial_handoff(), '', 1) == expected
    integration = record['proof_origin_integration']
    assert integration['canonical_document'] == 'source-index.html'
    assert integration['served_document_sha256'] == hashlib.sha256(served).hexdigest()
    assert integration['script_order'] == ['/scripts/szl-flow-proof.js', '/scripts/szl-holo-proof-v2.js']
    assert integration['page_stylesheet'] == 'proof-origin.css'
    assert integration['page_stylesheet_sha256'] == hashlib.sha256((ROOT / 'proof-origin.css').read_bytes()).hexdigest()
    assert integration['experiment_data_modified'] is False


def test_fresh_trial_handoff_keeps_runtime_and_frozen_evidence_separate():
    handoff = live_trial_handoff()
    assert handoff.count('<a ') == 1
    assert f'href="{WORKBENCH}"' in handoff
    assert 'Run a fresh trial' in handoff
    assert 'on-demand' in handoff and 'exploratory synthetic CPU inference' in handoff
    assert 'unsigned receipt' in handoff and '24 hours' in handoff and '128-record limit' in handoff
    assert 'lost on restart' in handoff and 'download yours' in handoff
    assert 'frozen <strong>FAILED</strong> benchmark unchanged' in handoff
    assert not re.search(r'<(?:script|iframe|form)\b', handoff, flags=re.IGNORECASE)
    record = json.loads((ROOT / 'publication.json').read_bytes())
    location = record['proof_origin_integration']['exploratory_workbench_handoff']
    assert location['url'] == WORKBENCH
    assert location['html_sha256'] == hashlib.sha256(handoff.encode('utf-8')).hexdigest()
    assert location['role'] == 'OFF_ORIGIN_EXPLORATORY_WORKBENCH_LOCATION'
    assert location['location_only'] is True
    assert location['execution_on_proof_origin'] is False
    assert location['new_trials_modify_registered_benchmark'] is False
    assert record['surface_role'] == 'STATIC_RECORDED_EVIDENCE_REPLAY'
    assert record['scientific_overall_gate'] == 'FAILED'
    assert record['model_inference_performed'] is False


if __name__ == '__main__':
    test_confirmation_mirror_preserves_frozen_release_and_all_data_hashes()
    test_publication_record_is_source_bound_and_preserves_provider_scope()
    test_fresh_trial_handoff_keeps_runtime_and_frozen_evidence_separate()
    print('OK: frozen confirmation evidence and canonical publication binding are intact.')
