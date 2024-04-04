import os
import re
import subprocess
import sys

import packaging.version

DOWNLOADS_DIR = "downloads"

GOOGLE_OIDC_PROVIDER = "https://accounts.google.com"
GITHUB_OIDC_PROVIDER = "https://github.com/login/oauth"


def tarballs_and_release_managers() -> list[tuple[str, str, str]]:
    """Iterate over all downloaded tarballs and yield their respective release manager identity+IdP"""
    global DOWNLOADS_DIR
    python_tarball_rms_ver = []
    for filename in sorted(os.listdir(DOWNLOADS_DIR)):
        if match := re.match(r"^Python-(([0-9.]+).*)(?:\.tar\.xz|\.tgz)$", filename):
            # Get the release manager based on version.
            int_version = tuple(map(int, match.group(2).split(".")))
            assert len(int_version) == 3

            # Table of release managers for 3.7 to 3.12
            if int_version < (3, 8):
                release_manager = "nad@python.org"
                identity_provider = GITHUB_OIDC_PROVIDER
            elif (3, 8) <= int_version < (3, 10):
                release_manager = "lukasz@langa.pl"
                identity_provider = GITHUB_OIDC_PROVIDER
            elif (3, 10) <= int_version < (3, 12):
                release_manager = "pablogsal@python.org"
                identity_provider = GOOGLE_OIDC_PROVIDER
            elif (3, 12) <= int_version < (3, 13):
                release_manager = "thomas@python.org"
                identity_provider = GOOGLE_OIDC_PROVIDER
            elif (3, 13) <= int_version < (3, 14):
                release_manager = "thomas@python.org"
                identity_provider = GOOGLE_OIDC_PROVIDER
            else:
                raise ValueError("Unknown release manager for release")

            # Create the package version for sorting.
            pkg_version = packaging.version.Version(match.group(1))
            python_tarball_rms_ver.append(
                (filename, release_manager, identity_provider, pkg_version)
            )

    # Only return the filename and release manager.
    # Strip off the packaging.version.Version() after sorting with it.
    return [
        (filename, release_manager, identity_provider)
        for (filename, release_manager, identity_provider, _) in sorted(
            python_tarball_rms_ver, key=lambda x: x[3]
        )
    ]


def signatures():
    print("## Sigstore signatures")
    print("| Artifact | Cert/Sig Material | Identity | Provider | Result | Details |")
    print("|-|-|-|-|-|-|")

    for filename, release_manager, identity_provider in tarballs_and_release_managers():
        filepath = os.path.join(DOWNLOADS_DIR, filename)
        has_crt = os.path.isfile(f"{filepath}.crt")
        has_sig = os.path.isfile(f"{filepath}.sig")
        has_bundle = os.path.isfile(f"{filepath}.sigstore")

        if has_crt != has_sig:
            print(
                f"| `{filename}` | `.sig+.crt` | `{release_manager}` | `{identity_provider}` | FAIL | `.sig/.crt not both present or absent` |"
            )

        elif has_crt and has_sig:
            status, failure_reason = sigstore(
                [
                    f"--cert-oidc-issuer {identity_provider}",
                    f"--certificate {filepath}.crt",
                    f"--signature {filepath}.sig",
                    f"--cert-identity {release_manager}",
                    f"{filepath}",
                ]
            )
            print(
                f"| `{filename}` | `.sig+.crt` | `{release_manager}` | `{identity_provider}` | {status} | {failure_reason} |"
            )

        if has_bundle:
            status, failure_reason = sigstore(
                [
                    f"--cert-oidc-issuer {identity_provider}",
                    f"--bundle {filepath}.sigstore",
                    f"--cert-identity {release_manager}",
                    f"{filepath}",
                ]
            )
            print(
                f"| `{filename}` | `.sigstore` | `{release_manager}` | `{identity_provider}` | {status} | {failure_reason} |"
            )

        if not any([has_sig, has_crt, has_bundle]):
            print(
                f"| `{filename}` | N/A | `{release_manager}` | `{identity_provider}` | N/A | |"
            )

    sys.stdout.flush()


def sigstore(args: list[str]) -> tuple[str, str]:
    """Run sigstore to verify as documented for Python releases"""
    args = [
        "python -m sigstore verify identity",
    ] + args
    proc = subprocess.run(
        " ".join(args), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if proc.returncode != 0:
        try:
            failure_reason = (
                "`"
                + re.search(r"reason=[\"\']([^\"]+)[\"\']", proc.stdout.decode()).group(
                    1
                )
                + "`"
            )
        except Exception:
            failure_reason = proc.stdout.decode()
    else:
        failure_reason = ""
    status = "PASS" if proc.returncode == 0 else "FAIL"
    return (status, failure_reason)


def sha256sums():
    global DOWNLOADS_DIR
    print("## Digests")
    print("```")
    sys.stdout.flush()

    for filename, *_ in tarballs_and_release_managers():
        os.system(f"cd downloads/ && sha256sum {filename}*")

    sys.stderr.flush()
    sys.stdout.flush()
    print("```")


def main():
    print("# Verify Python release sigstore signatures")

    signatures()
    sha256sums()


if __name__ == "__main__":
    main()
