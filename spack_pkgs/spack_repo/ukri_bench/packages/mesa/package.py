# Copyright 2026 Chris Richardson and Garth N. Wells.
#
# SPDX-License-Identifier: MIT

from spack_repo.builtin.packages.mesa.package import Mesa as BuiltinMesa

from spack.package import *


class Mesa(BuiltinMesa):
    """The builtin mesa package, with a patch so Mesa 24.3 and 25.0 build
    against glibc 2.43 (e.g. Ubuntu 26.04).

    glibc 2.43 declares the C23 once_flag and call_once in <stdlib.h>, which
    conflict with Mesa's C11 threads shim (src/c11/threads.h). The patch is
    upstream Mesa commit 179e744f ("c11/threads: fix build on c23"), which
    uses glibc's definitions when they exist and changes nothing otherwise.
    Remove this override once the pinned spack-packages has the fix.

    mesa is not a direct dependency of anything in this repository: it
    provides gl, which hip (ROCm builds of bench-dolfinx) depends on. A
    dependency patch (depends_on(..., patches=...)) cannot reach it, so the
    builtin package is overridden instead.
    """

    patch("c11-threads-c23.patch", when="@24.3:25.0")
