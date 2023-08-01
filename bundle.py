"""Script which can back-fill Sigstore bundles"""

import base64
import os

from sigstore._internal.rekor import RekorClient
from sigstore._internal.tuf import TrustUpdater
from sigstore._utils import PEMCert
from sigstore.verify import VerificationMaterials
from sigstore_protobuf_specs.dev.sigstore.bundle.v1 import Bundle

DOWNLOADS_DIR = "downloads"


def main():
    filenames = set(os.listdir(DOWNLOADS_DIR))

    files_to_bundle = []
    for filename in filenames:
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        if (
            os.path.isfile(f"{filepath}.sig")
            and os.path.isfile(f"{filepath}.crt")
            and not os.path.isfile(f"{filepath}.sigstore")
        ):
            files_to_bundle.append(filepath)

    rekor_client = RekorClient.production(TrustUpdater.production())
    for filepath in files_to_bundle:
        with (
            open(filepath, mode="rb") as input_,
            open(f"{filepath}.crt", mode="r") as crt,
            open(f"{filepath}.sig", mode="rb") as sig,
        ):
            materials = VerificationMaterials(
                input_=input_,
                cert_pem=PEMCert(crt.read()),
                signature=base64.b64decode(sig.read()),
                rekor_entry=None,
            )
            materials._rekor_entry = materials.rekor_entry(rekor_client)

        bundle: Bundle = materials.to_bundle()
        with open(f"{filepath}.sigstore", mode="w") as f:
            f.truncate()
            f.write(bundle.to_json())

        print(f"Created bundle for {filepath}")


if __name__ == "__main__":
    main()
