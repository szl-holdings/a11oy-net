# SPDX-License-Identifier: Apache-2.0
"""Offline proof-pointer contract. Never contact or alter a product runtime."""
from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://a11oy.net/notes/HF_TOOLING_PRODUCT_2026-09-11.md'
SOURCE = '71e056185ec3090ebe633727ec90c3bfbb19bc78'
FORGE = '74a8a07ced6c6b8697b31b7d0e482c4241d55880'


def validate(record: dict) -> None:
    """Assert exact dated pointers and no manufactured authority or receipt store."""
    rows = [row for row in record['evidence_notes'] if row.get('url') == URL]
    if len(rows) != 1:
        raise ValueError('missing_or_duplicate_tooling_record')
    row = rows[0]
    expected = {
        'kind': 'dated evidence-pointer note', 'evidence_class': 'REPORTED',
        'source_revision': SOURCE, 'forge_evaluation_source': FORGE,
        'hf_runtime_revision': 'cabf38a24003b9bedd165632c669a8e8881c746a',
        'product_view': 'https://a-11-oy.com/frontier-tooling',
        'product_api': 'https://a-11-oy.com/api/a11oy/v1/frontier-tooling',
        'public_readback_job': 'https://huggingface.co/jobs/SZLHOLDINGS/6aa3ee4e21047bf1b0375b45',
        'public_readback_sha256': '9fe0bdfc972cd2439221b057621807618fb092e1f23bd52310a092ef3cc5b9ca',
        'http_observations': 18,
        'source_asset_and_receipt_observation': 'PASS_WITH_EXPLICIT_HTML_AUGMENTATION_BOUNDARY',
        'signature_attestation': 'NOT_PERFORMED_BY_THIS_ORIGIN',
        'estate_release_state': 'PARTIAL_LYTE_PUBLICATION_FAILURE',
        'observation_window_utc': '2026-09-11T12:04:35.590970Z/2026-09-11T12:04:36.398848Z',
    }
    for key, value in expected.items():
        if type(row.get(key)) is not type(value) or row[key] != value:
            raise ValueError('tooling_pointer_or_boundary_mismatch')
    if row.get('production_model_admission') is not False:
        raise ValueError('unearned_production_authority')
    if record['status']['state'] != 'PARTIAL' or record['status']['live_chain'] != 'UNAVAILABLE':
        raise ValueError('unearned_whole_estate_claim')
    if record['status']['receipt_ids'] != [] or record['live_store']['hosted_here'] is not False:
        raise ValueError('receipt_store_boundary_changed')
    for flag in ('receipt_bodies_are_not_rehosted_here', 'this_origin_does_not_run_verification',
                 'this_origin_is_not_a_product_host'):
        if record['boundaries'][flag] is not True:
            raise ValueError('origin_roles_changed')


class ToolingRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / 'record.json').read_text(encoding='utf-8'))

    def test_dated_record(self):
        validate(self.record)

    def test_history_remains_dated_and_distinct(self):
        notes = self.record['evidence_notes']
        self.assertTrue(any(n['url'].endswith('LYTE_FORECAST_2026-09-10.md') for n in notes))
        self.assertTrue(any(n['url'].endswith('LYTE_FORECAST_DEPLOYMENT_2026-09-10.md') for n in notes))

    def test_changed_bindings_and_flags_fail(self):
        for key, value in [('source_revision', 'a' * 40), ('forge_evaluation_source', SOURCE),
                           ('public_readback_sha256', '0' * 64), ('production_model_admission', True),
                           ('http_observations', True), ('estate_release_state', 'GREEN'),
                           ('signature_attestation', 'SIGNED')]:
            data = copy.deepcopy(self.record)
            row = next(n for n in data['evidence_notes'] if n['url'] == URL)
            row[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(data)

    def test_duplicate_rejected(self):
        self.record['evidence_notes'].append(copy.deepcopy(self.record['evidence_notes'][-1]))
        with self.assertRaises(ValueError):
            validate(self.record)

    def test_no_receipt_rehosting(self):
        self.record['live_store']['hosted_here'] = True
        with self.assertRaises(ValueError):
            validate(self.record)

    def test_note_links_to_live_product_and_retains_bounds(self):
        note = (ROOT / 'notes/HF_TOOLING_PRODUCT_2026-09-11.md').read_text(encoding='utf-8')
        for value in (SOURCE, FORGE, '18 of 18', '36 Python tests', '1M-token training',
                      'unsigned', 'HOLD', 'lyte-services/issues/18', 'not a production-browser'):
            self.assertIn(value, note)
        self.assertIn('https://a-11-oy.com/frontier-tooling', note)
        self.assertNotIn('<script', note)


if __name__ == '__main__':
    unittest.main()
