"""Read-only cleanup check using the specifically user-authorized .env key.

Never prints credentials, public keys, pod details, or response bodies.
Only GET requests; writes a sanitized receipt beside this file.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
POD = 't4cb81ztfk0i8m'


def main():
    keys = []
    for line in Path(r'C:\Users\brian\Documents\Math Latex etc\.env').read_text(encoding='utf-8-sig').splitlines():
        name, sep, value = line.partition('=')
        if sep and 'RUNPOD' in name.upper() and ('KEY' in name.upper() or 'TOKEN' in name.upper()):
            keys.append(value.strip().strip('"').strip("'"))
    if len(keys) != 1:
        raise SystemExit('Ambiguous credential; no request made')

    def get(path):
        request = urllib.request.Request('https://api.runpod.io/v2/' + path,
                                         headers={'Authorization': 'Bearer ' + keys[0]})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, None

    receipt = {'checked_utc': datetime.now(timezone.utc).isoformat(),
               'action': 'read-only Runpod cleanup verification',
               'resource_mutations': 0, 'billed_compute_created': False,
               'prior_sandbox_attempts': {'v1_list_http_status': 403, 'v2_list_http_status': 403}}
    try:
        status, data = get('pods')
        receipt['list_http_status'] = status
        if status == 200:
            receipt['current_pod_count'] = len(data['pods'])
            receipt['has_next_page'] = data['pagination']['hasNextPage']
            receipt['experiment_pod_present'] = any(p['id'] == POD for p in data['pods'])
            receipt['experiment_pod_http_status'] = get('pods/' + POD)[0]
            key_status, key_data = get('account/ssh-keys')
            receipt['public_keys_http_status'] = key_status
            if key_status == 200:
                receipt['registered_public_key_count'] = len(key_data['keys'])
        receipt['status'] = ('PASS' if receipt.get('experiment_pod_http_status') == 404 and
                             receipt.get('has_next_page') is False and
                             receipt.get('experiment_pod_present') is False and
                             receipt.get('registered_public_key_count') == 0 else 'UNVERIFIED')
    except Exception as exc:
        receipt.update(status='UNVERIFIED', error_type=type(exc).__name__)
    (HERE / 'runpod_cleanup_check.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
