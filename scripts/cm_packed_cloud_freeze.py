"""Freeze the established panels from an identified source archive without Git.

The case generator, schedule and measurement engine remain those of the local
campaign. This adapter records archive provenance instead of inventing a Git
repository/commit on the worker. Replayed local fixtures are explicitly consumed.
"""
import argparse
import json
import platform
import sys

from scripts import cm_packed_queries_campaign as campaign


def freeze(output):
    archive = json.loads((campaign.ROOT / 'SOURCE_MANIFEST.json').read_text())
    for name, expected in archive['files'].items():
        if campaign.sha(campaign.ROOT / name) != expected:
            raise ValueError('source archive identity mismatch: ' + name)
    output.mkdir(parents=True, exist_ok=False)
    cases = campaign.cases()
    schedule = []
    for cohort in cases:
        for case in cases[cohort]:
            for q in ((32,) if case['task'] == 'cache' else (1, 16)):
                for repeat in range(campaign.REPEATS):
                    arms = campaign.methods(case)
                    for method in (arms if repeat % 2 == 0 else arms[::-1]):
                        schedule.append(dict(cohort=cohort, case=case['id'], q=q,
                                             repeat=repeat, method=method))
    campaign.write(output / 'FIXTURES.json', cases)
    campaign.write(output / 'FREEZE.json', dict(
        schema='cm-packed-queries-cloud-replay/v1', seed=campaign.SEED,
        repeats=campaign.REPEATS, sources=archive['files'], schedule=schedule,
        fixtures_sha256=campaign.sha(output / 'FIXTURES.json'),
        source_manifest_sha256=campaign.sha(campaign.ROOT / 'SOURCE_MANIFEST.json'),
        source_parent_checkpoint=archive['git_checkpoint'],
        checkpoint='Source archive; no Git repository on worker. File hashes identify dirty-source state.',
        python=sys.version, platform=platform.platform(),
        protocol=dict(scope='Consumed local synthetic panels rerun on an authorized cloud VM; no fresh data claim.',
                      cold='JSON decode, compile, bind, execute, digest/scalar delivery, cache and plan release',
                      warm='Same requests with resident plans/caches, separate from cold total',
                      process='Fresh-process lifecycle measured separately',
                      memory='Separate tracemalloc runs, not RSS; discard consumed chunks',
                      selection='Fixed cases, seed, nine paired repeats and prior chunk sizes; no tuning')))
    for name in archive['files']:
        destination = output / 'source' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((campaign.ROOT / name).read_bytes())
    print('Portable source freeze complete', len(schedule), 'cells', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=campaign.Path, required=True)
    freeze(parser.parse_args().output)
