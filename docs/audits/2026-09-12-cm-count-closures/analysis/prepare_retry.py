"""Keep the failed bootstrap frozen; extend only fetch time in a new transport."""
import json
from pathlib import Path
AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
controller='scripts/runpod_closure_research_controller_v2.py';remote='scripts/cm_closure_research_remote_v2.py'
text=(ROOT/'scripts/runpod_closure_research_controller.py').read_text().replace('cm_closure_research_remote.py','cm_closure_research_remote_v2.py')
with (ROOT/controller).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
text=(ROOT/'scripts/cm_closure_research_remote.py').read_text()
needle="'643b5b6c9614ee1d1daed4eb374a431a67514587'], 300)"
assert text.count(needle)==1
text=text.replace(needle,needle.replace('300','600'))
with (ROOT/remote).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
protocol=json.loads((AUDIT/'component-study-PROTOCOL.json').read_text())
protocol.update(controller=controller,remote=remote,retry_reason='attempt-003 failed at public fetch after 300 seconds; no correctness tests or measurements ran; extend only fetch timeout to 600 seconds')
with (AUDIT/'component-study-retry-PROTOCOL.json').open('x') as stream:json.dump(protocol,stream,indent=2);stream.write('\n')
