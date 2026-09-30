"""Additional capped, watchdog-protected development walks at larger n."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from bounded_trial import MEMORY_CAP_BYTES
from linux_preflight import SOURCE_FILES, digest, run_stress

ROOT = Path(__file__).resolve().parent


def run():
    if sys.platform != 'linux':
        raise SystemExit('Linux only')
    rows = []
    for n, steps in ((28, 40), (32, 20)):
        row = run_stress(n, steps)
        rows.append(row)
        counts = row.get('counts', {})
        if (row.get('status') != 'PASS' or
            row.get('effective_cap_bytes') != MEMORY_CAP_BYTES or
            row.get('baseline_live_size', 0) <= 907 or
            row.get('ending_live_size') != row.get('baseline_live_size') or
            counts.get('later_limit_failures', 0) == 0 or
            counts.get('sat_miter_checks') != counts.get('extra_root_miter_checks') or
            counts.get('fresh_structure_checks', 0) == 0):
            break
    result = {'utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS' if len(rows) == 2 and all(r['status'] == 'PASS' for r in rows) else 'FAIL',
              'formal_campaign_inputs_executed': 0,
              'worker_rlimit_as_bytes': MEMORY_CAP_BYTES,
              'source_hashes': {name: digest(ROOT / name) for name in SOURCE_FILES},
              'walks': rows}
    (ROOT / 'linux_scale_results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'walks': [
        {'n': r['n'], 'status': r['status'], 'initial_live_size': r.get('baseline_live_size'),
         'restored_live_size': r.get('ending_live_size'),
         'peak_rss_bytes': r.get('max_rss_bytes'), 'wall_seconds': r['wall_seconds']}
        for r in rows]}), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    run()
