import os
import re

import urllib3

http = urllib3.PoolManager()

resp = http.request("GET", "https://www.python.org/ftp/python")
versions = re.findall(r"href=\"([0-9][.0-9]*[0-9])/\"", resp.data.decode())

for version in versions:
    split_version = tuple(map(int, version.split(".")))

    if split_version < (3, 7, 14):
        continue
    print(f"Downloading {version}...")

    resp = http.request("GET", f"https://www.python.org/ftp/python/{version}")
    assert resp.status == 200
    data = resp.data.decode("utf-8")
    urls = re.findall(
        r"\"(Python-.+(?:\.tar\.xz|\.tgz)(?:\.crt|\.sig|\.sigstore)?)\"", data
    )
    for url in urls:
        if os.path.isfile(f"downloads/{url}"):
            continue
        # wget is faster than Python
        returncode = os.system(
            f"wget https://www.python.org/ftp/python/{version}/{url} --quiet -P downloads/"
        )
        if returncode != 0:
            # Run again without --quiet to show the error.
            os.system(
                f"wget https://www.python.org/ftp/python/{version}/{url} --verbose -P downloads/"
            )
