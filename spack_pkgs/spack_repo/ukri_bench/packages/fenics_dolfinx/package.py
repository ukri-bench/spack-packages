# Copyright 2026 Chris Richardson and Garth N. Wells.
#
# SPDX-License-Identifier: MIT

from spack_repo.builtin.packages.fenics_dolfinx.package import (
    FenicsDolfinx as BuiltinFenicsDolfinx,
)

from spack.package import *


class FenicsDolfinx(BuiltinFenicsDolfinx):
    """The builtin fenics-dolfinx package, with a patch so its headers compile
    with nvcc.

    nvcc 13 aborts with an internal error ("assertion failed at scope_stk.c
    ... update_template_param_symbol") on the abbreviated function template
    EntityMap::sub_topology_to_topology(CellRange auto&&, bool) in DOLFINx
    0.11. The patch rewrites it as an explicit template. The benchmark can
    be compiled with nvcc against a CPU build of DOLFINx, so the patch is
    applied for all variants.

    This overrides the builtin package because Spack cannot apply a
    dependency patch (depends_on(..., patches=...)) to a package in another
    repository.
    """

    patch("0.11-entitymap-nvcc.patch", when="@0.11")
