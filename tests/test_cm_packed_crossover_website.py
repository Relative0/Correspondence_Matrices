"""Crossover publication boundaries and evidence-tamper rejection."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'deliverables_n22_24/master_explainer_2026_08_03'
spec=importlib.util.spec_from_file_location('packed_publication',ROOT/'scripts/cm_packed_crossover_publication_verify.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PackedCrossoverWebsiteTests(unittest.TestCase):
    def test_all_rows_sources_and_phases_verify_with_explicit_failed_post_exit_gate(self):
        result=module.verify(SITE)
        self.assertEqual((result['trial_records'],result['matching_pairs']),(112,56))
        self.assertFalse(result['post_exit_gate_passed'])

    def tamper(self,change,message):
        target=SITE/module.RELATIVE/'summary.json'; real=Path.read_text
        def read(path,*args,**kwargs):
            text=real(path,*args,**kwargs)
            if path==target:
                value=json.loads(text);change(value);return json.dumps(value)
            return text
        with patch.object(Path,'read_text',read):
            with self.assertRaisesRegex(ValueError,message):module.verify(SITE)

    def test_rejects_incorrect_paired_ratio(self):
        self.tamper(lambda s:s['analyses'][0].update(paired_median_ratio=.1),'stale paired medians')

    def test_rejects_erased_preservation_failure(self):
        self.tamper(lambda s:s.update(post_exit_gate_passed=True),'claim boundary')

    def test_rejects_unsupported_native_claim(self):
        self.tamper(lambda s:s['native_route'].update(available=True),'claim boundary')


if __name__=='__main__':unittest.main()
