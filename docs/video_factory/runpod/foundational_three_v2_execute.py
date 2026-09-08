"""Configure the exact foundational-three v2 proposal for the hardened controller."""

from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foundational_three_execute as controller  # noqa: E402


def configure() -> None:
    controller.PACKAGE_ROOT = HERE / "foundational_three_v2"
    controller.PROPOSAL_ID = "cm-video-foundational-three-production-remote-v2"
    controller.AUTHORIZATION_ID = controller.PROPOSAL_ID + "-auth"
    controller.PROPOSAL_IDENTITY = "4fe3d358db5ed1ffe499214a7a0063024ac20551e165978cf6c70c9711d84cb6"
    controller.BUNDLE_SHA256 = "e0dbdb5933adfc9bde22e04b0a6806c9df7a8e848c75235e12fe8a4485c45838"
    controller.MANIFEST_IDENTITY = "6243361abb00239746c7894a3d3b16daca8f429a0b81eb5492058d336870c6c7"
    controller.POD_NAME_PREFIX = "cm-foundational-three-v2-"
    controller.RUN_ID_PREFIX = "runpod-foundational-three-v2-"


if __name__ == "__main__":
    configure()
    controller.main()
