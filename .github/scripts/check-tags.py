# Check that each version's git tag still points at its pinned commit.
# Usage: spack python check-tags.py <package> ...
import subprocess
import sys

import spack.repo

failed = False
for name in sys.argv[1:]:
    pkg_cls = spack.repo.PATH.get_pkg_class(name)
    for version, args in pkg_cls.versions.items():
        tag, commit = args.get("tag"), args.get("commit")
        if not (tag and commit):
            continue
        out = subprocess.run(
            ["git", "ls-remote", pkg_cls.git, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        # An annotated tag lists the tag object, then the commit it points at (^{})
        found = out[-2] if out else None
        status = "ok" if found == commit else f"MISMATCH (tag points at {found})"
        print(f"{name}@{version}: tag {tag} -> {commit[:12]} {status}")
        failed |= found != commit
sys.exit(1 if failed else 0)
