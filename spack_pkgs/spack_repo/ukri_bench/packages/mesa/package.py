# Copyright 2026 Chris Richardson and Garth N. Wells.
#
# SPDX-License-Identifier: MIT

from spack_repo.builtin.packages.mesa.package import Mesa as BuiltinMesa

from spack.package import *


class Mesa(BuiltinMesa):
    """The builtin mesa package, with a patch so Mesa 25.0 builds against
    glibc 2.43 (e.g. Ubuntu 26.04).

    glibc 2.43 declares the C23 once_flag and call_once in <stdlib.h>, which
    conflict with Mesa's C11 threads shim (src/c11/threads.h). The patch is
    upstream Mesa commit 179e744f ("c11/threads: fix build on c23"), which
    uses glibc's definitions when they exist. ROCm builds of bench-dolfinx
    need mesa (hip depends on gl).

    This overrides the builtin package because Spack cannot apply a
    dependency patch (depends_on(..., patches=...)) to a package in another
    repository.
    """

    patch("25.0-c11-threads-c23.patch", when="@25.0")
