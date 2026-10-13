"""Prepare a region-specific transport retry; does not launch a pod."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-13-cm-fair-feature-model'

def main():
    old=ROOT/'scripts/runpod_fair_feature_model_controller_v3.py'
    new=ROOT/'scripts/runpod_fair_feature_model_controller_v4.py'
    source=old.read_text().replace('fair-feature-model-v3','fair-feature-model-v3-jp')
    marker="        payload = transport.create_payload(state['name'], offer, token, created)"
    assert source.count(marker)==1
    source=source.replace(marker,marker+"\n        payload['dataCenterIds'] = ['AP-JP-1']\n        payload['dataCenterPriority'] = 'custom'\n        record['requested_data_center'] = 'AP-JP-1'")
    marker="        record['actual_resources'] = resources"
    assert source.count(marker)==1
    source=source.replace(marker,"        if machine_id == '52izyrj03ple': raise RuntimeError('previously unready host reassigned')\n"+marker)
    with new.open('x') as stream: stream.write(source)
    packages=AUDIT/'packages'
    bundle=packages/'fair-feature-model-v3-jp.zip'
    with bundle.open('xb') as stream: stream.write((packages/'fair-feature-model-v3.zip').read_bytes())
    freeze=json.loads((packages/'fair-feature-model-v3-FREEZE.json').read_bytes())
    freeze['controller_sha256']=hashlib.sha256(new.read_bytes()).hexdigest()
    with (packages/'fair-feature-model-v3-jp-FREEZE.json').open('x') as stream:
        json.dump(freeze,stream,indent=2)
    print(json.dumps(dict(profile='fair-feature-model-v3-jp',identical_bundle=True,
        change='Request AP-JP-1 using documented dataCenterIds/dataCenterPriority; reject the previously unready machine.',
        documentation='https://docs.runpod.io/api-reference/pods/POST/pods')))

if __name__=='__main__': main()
