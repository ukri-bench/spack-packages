# Copyright 2025 Chris Richardson and Garth N. Wells.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage
from spack_repo.builtin.build_systems.rocm import ROCmPackage

from spack.package import *


class BenchDolfinx(CMakePackage, CudaPackage, ROCmPackage):
    "A benchmark using DOLFINx."

    homepage = "https://github.com/ukri-bench/ukri-bench"
    git = "https://github.com/ukri-bench/benchmark-dolfinx.git"

    version("main", tag="main", no_cache=True)

    depends_on("c", type="build")
    depends_on("cxx", type="build")

    depends_on("fenics-dolfinx@0.10")
    depends_on("fenics-basix")
    depends_on("py-fenics-ffcx", type="build")

    depends_on("boost +program_options")  # See https://github.com/boostorg/math/issues/1285
    depends_on("jsoncpp")
    depends_on("mpi")

    depends_on("cuda", when="+cuda")
    depends_on("hip", when="+rocm")
    conflicts("+cuda", when="+rocm", msg="Cannot build for both ROCm and CUDA.")

    with when("+rocm"):
        depends_on("rocm-core")
        depends_on("rocthrust")

    root_cmakelists_dir = "src"

    def cmake_args(self):
        args = []
        if "+rocm" in self.spec:
            args.append(
                self.define("HIP_ARCH", self.spec.variants["amdgpu_target"].value)
            )
        if "+cuda" in self.spec:
            args.append(self.define("CUDA_ARCH", self.spec.variants["cuda_arch"].value))
        return args
