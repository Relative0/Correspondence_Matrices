"""Package new execution wrappers around the sealed preparation archives."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/audits/2026-09-12-cm-component-execution'
PREPARED = ROOT / 'build/cm-diag/docs/audits/2026-09-12-component-diagnostics'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def prepare():
    assert sha(PREPARED / 'FINAL-MANIFEST.json') == '2ddd1ee881f60cff7cde9564e1aec359bb68385cd8685335f0e0faf6b9e9ee57'
    write(AUDIT / 'AUTHORIZATION.json', dict(
        user_instruction='Ok, please continue. If you mean budget, I authorize up to $5 on Runpod. I am not sure what the missing exact backend is, but if it is needed, please find it.',
        scope='RunPod component diagnostics, frozen historical source checks, and Decisionmaking projected decomposition; no publication.',
        additional_runpod_budget_usd=5.0, prior_nonrefunded_reservations_usd=10.0,
        cumulative_cap_usd=15.0, attempt_reservation_usd=.50,
        reservations_are_not_refunded_by_estimated_costs=True))
    packages = AUDIT / 'packages'
    packages.mkdir(exist_ok=False)
    with zipfile.ZipFile(ROOT / 'docs/audits/2026-09-12-cm-count-closures/packages/component-study.zip') as archive:
        dependencies = [d for d in json.loads(archive.read('DEPENDENCIES.json'))
                        if d['name'].lower() in ('numpy', 'pytest', 'packaging', 'pluggy', 'iniconfig', 'pygments')]
    assert len(dependencies) == 6
    entries = {}
    archives = []
    sealed = {r['path']: r for r in json.loads((PREPARED / 'FINAL-MANIFEST.json').read_bytes())['artifacts']}
    for source, target in [('component-paired-replay.zip', 'component'), ('h6-replay.zip', 'h6'),
                           ('decisionmaking-partition-replay.zip', 'partition')]:
        entries[source] = (PREPARED / source).read_bytes()
        assert len(entries[source]) == sealed[source]['bytes']
        assert hashlib.sha256(entries[source]).hexdigest() == sealed[source]['sha256']
        archives.append(dict(path=source, destination=target))
    supplements = []
    for relative in ['scripts/cm_application_oracle.py', 'scripts/cm_decisionmaking_partition_run.py',
                     'docs/audits/2026-09-12-cm-application-evidence/ORACLE-PROTOCOL.json']:
        name = 'supplement/' + relative
        entries[name] = (ROOT / 'build/cm-diag' / relative).read_bytes()
        supplements.append(dict(path=name, destination='component/' + relative))
    entries['DEPENDENCIES.json'] = (json.dumps(dependencies, indent=2) + '\n').encode()
    protocol = dict(schema='cm-component-execution/v1', additional_paid_authorization_usd=5,
        sealed_preparation_unchanged=True, prepared_manifest_sha256=sha(PREPARED / 'FINAL-MANIFEST.json'),
        interpretation='Component cases are exposed development evidence. H6 is restored-source compatibility replay on Python 3.13.15, not the recorded 3.13.5 interpreter.',
        lifetime_s=4800, cleanup_horizon_s=5100, reservation_usd=.50,
        archives=archives, supplements=supplements,
        files=[dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(entries.items())])
    entries['EXECUTION-PROTOCOL.json'] = (json.dumps(protocol, indent=2) + '\n').encode()
    bundle = packages / 'component-historical.zip'
    with zipfile.ZipFile(bundle, 'x', zipfile.ZIP_STORED) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
    assert bundle.stat().st_size < 32 << 20
    write(packages / 'EXECUTION-PROTOCOL.json', protocol)
    write(packages / 'component-historical-FREEZE.json', dict(
        bundle_sha256=sha(bundle), bytes=bundle.stat().st_size,
        controller_sha256=sha(ROOT / 'scripts/runpod_component_diagnostics_controller.py'),
        remote_sha256=sha(ROOT / 'scripts/cm_component_execution_remote.py'),
        transport_sha256=sha(ROOT / 'scripts/runpod_query_ladder_q64_second_host_v3_controller.py'),
        bootstrap_sha256=sha(ROOT / 'scripts/runpod_frontier_bootstrap.py'),
        prepare_sha256=sha(Path(__file__))))
    print(json.dumps(dict(bundle=str(bundle), bytes=bundle.stat().st_size, sha256=sha(bundle))))


if __name__ == '__main__':
    prepare()
