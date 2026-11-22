# Print the packages written in the ukri_bench repository, leaving out
# packages that override a builtin package (e.g. fenics-dolfinx, which is
# the builtin package plus a patch).
# Usage: spack python repo-packages.py
import spack.repo

builtin = spack.repo.PATH.get_repo("builtin")
ukri_bench = spack.repo.PATH.get_repo("ukri_bench")
print(" ".join(n for n in ukri_bench.all_package_names() if not builtin.exists(n)))
