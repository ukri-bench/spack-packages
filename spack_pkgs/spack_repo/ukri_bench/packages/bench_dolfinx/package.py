# Copyright 2025 Chris Richardson and Garth N. Wells.
#
# SPDX-License-Identifier: MIT

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage
from spack_repo.builtin.build_systems.rocm import ROCmPackage

from spack.package import *


class BenchDolfinx(CMakePackage, CudaPackage, ROCmPackage):
    """A benchmark using DOLFINx."""

    homepage = "https://github.com/ukri-bench/benchmark-dolfinx"
    git = "https://github.com/ukri-bench/benchmark-dolfinx.git"

    version("main", branch="main", no_cache=True)
    version("0.10.0", tag="v0.10.0", commit="2f148fdda9e40af17fdf7a936b7357350ba41600")

    conflicts("+cuda", when="+rocm", msg="Cannot build for both ROCm and CUDA.")
    # The benchmark CMake treats an unset GPU arch as a CPU-only build
    conflicts("cuda_arch=none", when="+cuda", msg="A CUDA architecture must be specified.")
    conflicts("amdgpu_target=none", when="+rocm", msg="An AMD GPU target must be specified.")

    depends_on("c", type="build")
    depends_on("cxx", type="build")

    depends_on("fenics-dolfinx partitioners:=scotch")
    # Benchmark version -> DOLFINx/Basix/FFCx version. FFCx-generated code must
    # match the UFCx interface of DOLFINx.
    for ver, fenics_ver in [("0.10", "0.10"), ("main", "0.11")]:
        depends_on(f"fenics-dolfinx@{fenics_ver}", when=f"@{ver}")
        depends_on(f"fenics-basix@{fenics_ver}", when=f"@{ver}")
        depends_on(f"py-fenics-ffcx@{fenics_ver}", type="build", when=f"@{ver}")

    depends_on("boost +program_options+json")
    # Not used directly; selects 64-bit Scotch for DOLFINx graph partitioning
    depends_on("scotch +int64")
    depends_on("mpi")

    with when("+rocm"):
        depends_on("rocm-core")
        depends_on("rocthrust")

    root_cmakelists_dir = "src"

    def cmake_args(self):
        args = []
        if self.spec.satisfies("+rocm"):
            args.append(self.define_from_variant("HIP_ARCH", "amdgpu_target"))
        if self.spec.satisfies("+cuda"):
            args.append(self.define_from_variant("CUDA_ARCH", "cuda_arch"))
        return args
