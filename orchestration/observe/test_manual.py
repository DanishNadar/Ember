"""No training: validate controls and prove all launch guards with mocked CLI."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from orchestration.observe import manual


class ManualTests(unittest.TestCase):
    def options(self):
        c = yaml.safe_load((manual.ROOT / 'ml/arrival_config.yaml').read_text())
        return dict(experiment_name='unit-only',config=c,mode='single',optimizer='Adam',fine_tune=False,
                    dataset='missing-test-dataset',output_root='missing-output',generate_physics=False,
                    cpu_workers=4,physics_scenarios_per_region=1,physics_uri='',trial_learning_rates=[.001,.0003])

    def test_invalid_controls_fail_before_any_cli_call(self):
        for key,value in [('epochs',0),('learning_rate',float('nan')),('threshold',1),('dropout',1)]:
            o=self.options();o['config'][key]=value
            with patch.object(manual,'command') as cli, self.assertRaises(ValueError):manual.preflight(o)
            cli.assert_not_called()

    def test_missing_dataset_and_unverified_modes_fail(self):
        for mode in ['single','ddp']:
            o=self.options();o['mode']=mode
            with self.assertRaises(ValueError):manual.validate(o)

    def test_preview_contains_only_requested_jobs(self):
        o=self.options();self.assertEqual(len(manual.preview(o)['jobs']),1)
        o['mode']='independent';self.assertEqual(len(manual.preview(o)['jobs']),2)
        o['generate_physics']=True;self.assertEqual(len(manual.preview(o)['jobs']),4)

    def test_launch_defaults_to_dry_run_and_requires_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t);(run/'options.json').write_text(json.dumps(self.options()))
            with patch.object(manual,'command') as cli:
                self.assertFalse(manual.launch(run)['submitted'])
                with self.assertRaises(ValueError):manual.launch(run,dry_run=False)
                cli.assert_not_called()

    def test_staging_requires_separate_confirmation(self):
        with patch.object(manual,'command') as cli, self.assertRaises(ValueError):manual.stage_inputs('unused')
        cli.assert_not_called()

    def test_preflight_failure_never_submits(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t);o=self.options();(run/'options.json').write_text(json.dumps(o))
            (run/'input.tgz').write_bytes(b'fixture')
            (run/'workflow.fz').write_text(yaml.safe_dump(manual.preview(o)))
            (run/'provenance.json').write_text(json.dumps({key:manual.sha(run/file) for file,key in
                [('input.tgz','input_sha256'),('options.json','options_sha256'),('workflow.fz','workflow_sha256')]}))
            with patch.object(manual,'preflight',side_effect=ValueError('no free GPU')), patch.object(manual,'command') as cli:
                with self.assertRaisesRegex(ValueError,'no free GPU'):manual.launch(run,confirmation=o['experiment_name'],dry_run=False)
                cli.assert_not_called()

    def test_confirmed_mock_launch_submits_once_and_prevents_retry(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t);o=self.options();(run/'options.json').write_text(json.dumps(o))
            (run/'input.tgz').write_bytes(b'fixture');(run/'workflow.fz').write_text('version: v4')
            prov={key:manual.sha(run/file) for file,key in
                  [('input.tgz','input_sha256'),('options.json','options_sha256'),('workflow.fz','workflow_sha256')]}
            prov['dataset_manifest_sha256']='fixture-manifest'
            (run/'provenance.json').write_text(json.dumps(prov))
            def cli(*args):
                if args[:2]==('workflow','list'):return '[]'
                if args[:2]==('object','describe'):return json.dumps({'digest':prov['input_sha256']})
                if args[:2]==('workflow','start'):return '{"ID":"mock-only"}'
                return 'validated'
            with patch.object(manual,'preflight',return_value={'dataset_manifest_sha256':'fixture-manifest'}), patch.object(manual,'command',side_effect=cli) as call:
                self.assertEqual(manual.launch(run,confirmation=o['experiment_name'],dry_run=False)['ID'],'mock-only')
                with self.assertRaises(ValueError):manual.launch(run,confirmation=o['experiment_name'],dry_run=False)
                self.assertEqual(sum(c.args[:2]==('workflow','start') for c in call.call_args_list),1)

if __name__=='__main__':unittest.main()
