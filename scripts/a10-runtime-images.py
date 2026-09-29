"""Run on the staging Docker host: compare running image IDs with pinned digests.

No container mutation, environment dump, or reliance on /instance declarations.
The caller supplies only container names, image digests and the expected revision.
"""

import json
import re
import subprocess
import sys


def inspect(kind, name):
    return json.loads(
        subprocess.check_output(["docker", kind, "inspect", name], text=True)
    )[0]


def main():
    revision, api_name, api_image, web_name, web_image = sys.argv[1:]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("expected full release SHA")
    result = {"releaseSha": revision, "containers": {}}
    for role, name, image in (
        ("api", api_name, api_image),
        ("web", web_name, web_image),
    ):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise ValueError("invalid container name")
        if not re.fullmatch(r"[a-z0-9./_-]+@sha256:[0-9a-f]{64}", image):
            raise ValueError("expected repository image digest")
        container = inspect("container", name)
        expected = inspect("image", image)
        if not container["State"]["Running"] or container["Image"] != expected["Id"]:
            raise RuntimeError(
                f"{role}: running container differs from requested digest"
            )
        if (
            expected.get("Config", {})
            .get("Labels", {})
            .get("org.opencontainers.image.revision")
            != revision
        ):
            raise RuntimeError(f"{role}: image revision differs from release SHA")
        result["containers"][role] = {
            "name": name,
            "image": image,
            "imageId": expected["Id"],
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
