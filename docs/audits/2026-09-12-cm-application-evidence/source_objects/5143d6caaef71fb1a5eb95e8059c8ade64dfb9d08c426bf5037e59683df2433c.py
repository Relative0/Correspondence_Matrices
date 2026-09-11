"""Instrument an explicitly selected actual foundational render (opt-in).

Run this inside the next independently needed, authorized production job.
It does not reconstruct a historical trace or authorize video publication.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cmbench.comparative.presentation_capture import capture_presentation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--producer-sha256', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--purpose', choices=('production', 'controlled_replay'), required=True)
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    source = args.producer.resolve()
    if hashlib.sha256(source.read_bytes()).hexdigest() != args.producer_sha256:
        parser.error('producer source identity mismatch')
    output = args.output_root.resolve()
    if output.exists():
        parser.error('use a fresh output directory for this production receipt')
    if args.receipt.exists():
        parser.error('receipt already exists')
    spec = importlib.util.spec_from_file_location('observed_foundational_producer', source)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(source.parent))
    spec.loader.exec_module(module)
    with capture_presentation(module, args.receipt, source_sha256=args.producer_sha256,
                              purpose=args.purpose) as receipt:
        module.render_full(output_root=output, width=args.width, height=args.height,
                           workers=args.workers, keep_frames=False)
        manifest = output/'render_summary.json'
        receipt.update(status='complete', output_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
