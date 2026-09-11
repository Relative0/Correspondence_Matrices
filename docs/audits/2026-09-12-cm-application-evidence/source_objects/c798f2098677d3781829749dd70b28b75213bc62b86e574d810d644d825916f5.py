"""Opt-in receipts at the real foundational video's presentation boundary.

These calls format supplied bit strings. They do not measure model counting,
matrix materialization, or downstream rendering speed.
"""
from contextlib import contextmanager
from functools import wraps
from .consumer_capture import ConsumerCapture


def normalized(value):
    """Normalize formatter sets without changing arguments passed to it."""
    if isinstance(value, set):
        if any(type(item) is not int for item in value):
            raise ValueError('formatter sets must contain integer cell indices')
        return {'set_of_cell_indices': sorted(value)}
    if isinstance(value, (tuple, list)):
        return [normalized(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError('formatter keyword keys must be strings')
        return {key: normalized(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise ValueError('unsupported formatter argument')


@contextmanager
def capture_presentation(module, path, *, source_sha256, purpose):
    names = ('matrix', 'mini_matrix')
    originals = {name: getattr(module, name) for name in names}
    if any(not callable(value) for value in originals.values()):
        raise ValueError('expected foundational formatter functions')
    capture = ConsumerCapture(path, caller_sha256=source_sha256, purpose=purpose)
    result = {'status': 'failed', 'output_manifest_sha256': None}

    def observe(name, original):
        @wraps(original)
        def wrapped(*args, **kwargs):
            # Only the digest input is normalized; the original receives the
            # exact original objects, including sets and shared references.
            request = [name, normalized(args), normalized(kwargs)]
            def invoke(_request):
                return original(*args, **kwargs)
            return capture.wrap(invoke)(request)
        return wrapped

    try:
        for name, original in originals.items():
            setattr(module, name, observe(name, original))
        yield result
    finally:
        for name, original in originals.items():
            setattr(module, name, original)
        capture.close(**result)
