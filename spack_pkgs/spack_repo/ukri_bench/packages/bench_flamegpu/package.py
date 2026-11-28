# Copyright 2026 Garth N. Wells.
#
# SPDX-License-Identifier: MIT

import re

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage
from spack_repo.builtin.build_systems.rocm import ROCmPackage

from spack.package import *

# FLAME GPU 2 commit used by benchmark-flamegpu (FLAMEGPU_VERSION in its
# CMakeLists.txt): the merge of the amdgpu branch, which added the HIP backend.
# FLAME GPU has no install rules, so the benchmark builds it as a subproject.
FLAMEGPU_COMMIT = "4fa74199ad0623642b51c9e49fad3884c23f5419"


class BenchFlamegpu(CMakePackage, CudaPackage, ROCmPackage):
    """Agent-based simulation benchmarks using FLAME GPU 2."""

    homepage = "https://github.com/ukri-bench/benchmark-flamegpu"
    git = "https://github.com/ukri-bench/benchmark-flamegpu.git"

    maintainers("ptheywood", "Robadob", "mondus")

    license("AGPL-3.0-only")

    version("main", branch="main", no_cache=True)
    version("0.1.0", tag="v0.1.0", commit="f56e54656b794c826a572dd3b612f5eac65ef06a")

    variant(
        "seatbelts",
        default=False,
        description="FLAME GPU runtime error checking (slower; for debugging models)",
    )

    requires("+cuda", "+rocm", policy="one_of", msg="Build with either +cuda or +rocm.")
    conflicts("cuda_arch=none", when="+cuda", msg="A CUDA architecture must be specified.")

    depends_on("cxx", type="build")
    depends_on("cmake@3.25.2:", type="build")
    # The benchmark records `git describe` of its source in its output
    depends_on("git", type="build")

    depends_on("cli11@2.5:")
    depends_on("nlohmann-json@3.11.3:")
    depends_on("tinyxml2@9:")

    with when("+cuda"):
        depends_on("cuda@12.4:")
        # FLAME GPU needs CCCL 3, which CUDA bundles from 13.0
        depends_on("cccl@3:", when="^cuda@:12")
        # C++20 with nvcc
        conflicts("%cxx=gcc@:10")

    with when("+rocm"):
        depends_on("hip@7:")
        depends_on("rocthrust")
        depends_on("hipcub")
        depends_on("hiprand")
        depends_on("rocm-smi-lib")
        # hip::device adds `-x hip` to every target, C++ sources included
        requires("%cxx=llvm-amdgpu", msg="ROCm builds need the ROCm (llvm-amdgpu) C++ compiler.")

    resource(
        name="flamegpu2",
        git="https://github.com/FLAMEGPU/FLAMEGPU2.git",
        commit=FLAMEGPU_COMMIT,
        placement="flamegpu2",
    )
    # Fetched by FLAME GPU's cmake/dependencies/Jitify.cmake (CUDA only), which
    # expects the source in a directory named `jitify`. Not in builtin.
    resource(
        name="jitify",
        git="https://github.com/NVIDIA/jitify.git",
        commit="44e978b21fc8bdb6b2d7d8d179523c8350db72e5",
        destination="jitify-src",
        placement="jitify",
        when="+cuda",
    )

    @run_before("cmake")
    def check_flamegpu_commit(self):
        """Fail if the benchmark expects a different FLAME GPU than the resource."""
        with open(join_path(self.stage.source_path, "CMakeLists.txt")) as f:
            match = re.search(r'set\(FLAMEGPU_VERSION "([^"]+)"', f.read())
        if match and match.group(1) != FLAMEGPU_COMMIT:
            raise InstallError(
                f"benchmark-flamegpu expects FLAME GPU {match.group(1)}, but the package "
                f"provides {FLAMEGPU_COMMIT}. Update FLAMEGPU_COMMIT in bench-flamegpu."
            )

    def cmake_args(self):
        spec = self.spec
        src = self.stage.source_path
        args = [
            self.define("FLAMEGPU_ROOT", join_path(src, "flamegpu2")),
            # Find tinyxml2, CLI11 and nlohmann-json from Spack
            self.define("USE_SPACK_FLAMEGPU2_DEPS", True),
            # Fail rather than download anything not provided by Spack
            self.define("FETCHCONTENT_FULLY_DISCONNECTED", True),
            self.define_from_variant("FLAMEGPU_SEATBELTS", "seatbelts"),
        ]
        if spec.satisfies("+cuda"):
            args += [
                self.define("FLAMEGPU_BACKEND", "CUDA"),
                self.define_from_variant("CMAKE_CUDA_ARCHITECTURES", "cuda_arch"),
                self.define(
                    "FETCHCONTENT_SOURCE_DIR_JITIFY", join_path(src, "jitify-src", "jitify")
                ),
            ]
        if spec.satisfies("+rocm"):
            args += [
                self.define("FLAMEGPU_BACKEND", "HIP"),
                self.define_from_variant("CMAKE_HIP_ARCHITECTURES", "amdgpu_target"),
                self.define(
                    "CMAKE_HIP_COMPILER",
                    join_path(spec["llvm-amdgpu"].prefix.bin, "amdclang++"),
                ),
            ]
        return args
