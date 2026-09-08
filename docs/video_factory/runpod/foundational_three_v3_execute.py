"""Configure the exact foundational-three v3 narrated proposal controller."""

from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foundational_three_execute as controller  # noqa: E402


def configure() -> None:
    controller.PACKAGE_ROOT = HERE / "foundational_three_v3"
    controller.PROPOSAL_ID = "cm-video-foundational-three-production-remote-v3"
    controller.AUTHORIZATION_ID = controller.PROPOSAL_ID + "-auth"
    controller.PROPOSAL_IDENTITY = "e15b8b08b7ad0921803176ff48b8024c7105e9b42e17182d409cc0c0c6d2bde1"
    controller.BUNDLE_SHA256 = "c9cf680f9586db02d61c58fe32157122d7adaf74b08c2263eced23126a68e292"
    controller.PACKAGE_IDENTITY = "3e563a05874882654158f16a738096532d642f72465a155927ca94c5ab538402"
    controller.MANIFEST_IDENTITY = "5aecfa35c260d47046296a537905c64abb00283112caaca1507532368dd43177"
    controller.POD_NAME_PREFIX = "cm-foundational-three-v3-"
    controller.RUN_ID_PREFIX = "runpod-foundational-three-v3-"
    controller.EXPECTED = {
        "operator-cms-from-truth-tables": {
            "duration": 219,
            "frames": 6570,
            "content_hash": "a603c8e3c672edb3a02103f869b40d9220d2ee756e377c59112e633ca1dd9072",
        },
        "logical-matrices-to-higher-dimensional-cms": {
            "duration": 265,
            "frames": 7950,
            "content_hash": "e21825e9c1d981b260a30a35f721f427278c28ee0c0675e281355ba4c6c42fcb",
        },
        "what-is-explicit-cm": {
            "duration": 220,
            "frames": 6600,
            "content_hash": "a1f123414508f4892033336906dc7ea11b80fab3c9be4f9ae8441f1884e0ff53",
        },
    }


if __name__ == "__main__":
    configure()
    controller.main()
