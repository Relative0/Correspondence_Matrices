"""Run the maintained video compiler with local call receipts (opt-in only)."""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cmbench.comparative.consumer_capture import ConsumerCapture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--purpose',choices=('production','controlled_replay'),required=True)
    parser.add_argument('compiler_arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    forwarded=args.compiler_arguments
    if forwarded[:1]==['--']:forwarded=forwarded[1:]
    if not forwarded or forwarded[0]!='build':
        parser.error('forward the compiler build command and its --pop-root argument')
    source=ROOT/'docs/video_factory/deep_series_chapter_compiler.py'
    sys.path.insert(0,str(source.parent))
    import deep_series_chapter_compiler as compiler
    capture=ConsumerCapture(args.output,caller_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),purpose=args.purpose)
    original=compiler.truth_layout_payload
    compiler.truth_layout_payload=capture.wrap(original)
    prior_argv=sys.argv
    sys.argv=[str(source),*forwarded]
    status='failed';manifest_sha=None
    try:
        compiler.main()
        manifest=compiler.WP1_ROOT/'chapter_render_contract_manifest.json'
        manifest_sha=hashlib.sha256(manifest.read_bytes()).hexdigest()
        status='complete'
    finally:
        sys.argv=prior_argv
        compiler.truth_layout_payload=original
        capture.close(status=status,output_manifest_sha256=manifest_sha)


if __name__=='__main__':main()
