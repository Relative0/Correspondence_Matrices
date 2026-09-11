"""Opt-in, local, bounded call receipts; provenance admission remains separate.

Receipts contain digests and call outcomes, never arguments or returned values.
An operator's purpose declaration is an attestation, not proof of natural use.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
from pathlib import Path
import time
import uuid


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class ConsumerCapture:
    def __init__(self,path: Path,*,caller_sha256: str,purpose: str,max_events: int=20000):
        if purpose not in ('production','controlled_replay'):
            raise ValueError('explicit operator purpose required')
        if len(caller_sha256)!=64 or any(c not in '0123456789abcdef' for c in caller_sha256):
            raise ValueError('invalid caller source digest')
        if type(max_events) is not int or not 1<=max_events<=20000:
            raise ValueError('invalid event limit')
        self.path=Path(path)
        self.stream=self.path.open('x',encoding='utf-8',newline='\n')
        self.previous='0'*64
        self.calls=0;self.dropped=0;self.max_events=max_events;self.closed=False
        self._write(dict(kind='start',schema='cm-consumer-capture/v1',session=uuid.uuid4().hex,
            utc=datetime.now(timezone.utc).isoformat(),caller_sha256=caller_sha256,
            operator_attested_purpose=purpose,admission='pending_independent_review',
            scope='sequential calls and returned output identities; reuse or downstream consumption not inferred'))

    def _write(self,row):
        row=dict(row,previous_sha256=self.previous)
        self.previous=digest(row)
        self.stream.write(json.dumps(dict(row,sha256=self.previous),sort_keys=True)+'\n')
        self.stream.flush()

    def wrap(self,function):
        @wraps(function)
        def observed(*args,**kwargs):
            if self.closed:raise RuntimeError('capture already closed')
            if self.calls>=self.max_events:
                self.dropped+=1
                return function(*args,**kwargs)
            self.calls+=1;sequence=self.calls
            request=digest([args,kwargs]);start=time.perf_counter_ns()
            try:
                value=function(*args,**kwargs)
            except BaseException as exc:
                self._write(dict(kind='call',sequence=sequence,request_sha256=request,
                    elapsed_ns=time.perf_counter_ns()-start,status='raised',exception_type=type(exc).__name__))
                raise
            # Measure the consumer call only; JSON hashing and receipt I/O are
            # observer overhead and must not be mistaken for benchmark speed.
            elapsed=time.perf_counter_ns()-start
            self._write(dict(kind='call',sequence=sequence,request_sha256=request,
                elapsed_ns=elapsed,status='returned',output_sha256=digest(value)))
            return value
        return observed

    def close(self,*,status,output_manifest_sha256=None):
        if self.closed:return
        self._write(dict(kind='end',utc=datetime.now(timezone.utc).isoformat(),status=status,
            recorded_calls=self.calls,dropped_calls=self.dropped,complete=self.dropped==0,
            output_manifest_sha256=output_manifest_sha256))
        self.stream.close();self.closed=True


def verify_capture(path: Path):
    """Verify custody/completeness without promoting operator intent to evidence."""
    if path.stat().st_size>16<<20:raise ValueError('capture size exceeded')
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    if len(rows)<2 or rows[0].get('kind')!='start' or rows[-1].get('kind')!='end':
        raise ValueError('incomplete capture')
    previous='0'*64
    for row in rows:
        expected=row.pop('sha256')
        if row.get('previous_sha256')!=previous or digest(row)!=expected:raise ValueError('capture chain mismatch')
        previous=expected
    calls=rows[1:-1]
    if any(r.get('kind')!='call' or r.get('sequence')!=i+1 for i,r in enumerate(calls)):
        raise ValueError('call sequence mismatch')
    end=rows[-1]
    if end['recorded_calls']!=len(calls) or not end['complete'] or end['dropped_calls']:
        raise ValueError('truncated capture')
    return dict(recorded_calls=len(calls),status=end['status'],sha256=previous,
        operator_attested_purpose=rows[0]['operator_attested_purpose'],
        natural_use_admitted=False,reason='independent provenance and downstream-use review required')
