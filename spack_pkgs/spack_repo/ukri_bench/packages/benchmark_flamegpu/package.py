# SPDX-License-Identifier: MIT

import os

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage
from spack_repo.builtin.build_systems.rocm import ROCmPackage

from spack.package import *


class BenchmarkFlamegpu(CMakePackage, CudaPackage, ROCmPackage):
    "A benchmark using FLAMEGPU2 as part of the UKRI living benchmarks project (https://ukri-bench.github.io)"

    homepage = "https://github.com/ukri-bench/benchmark-flamegpu"
    git = "https://github.com/ukri-bench/benchmark-flamegpu.git"

    maintainers("ptheywood", "mondus", "robadob")

    license("AGPL-3.0-only")

    version("main", branch="main", no_cache=True)

    variant(
        "seatbelts",
        default=False,
        description=(
            "Enable / Disable FLAMEGPU_SEATBELTS - additional runtime checks which harm "
            "performance but increase usability."
        ),
    )
    variant(
        "profiling",
        default=False,
        description="Enable NVTX/ROCTx markers for improved profiling",
    )
    variant(
        "telemetry",
        default=False,
        description=(
            "Share usage statistics telemetry (https://docs.flamegpu.com/guide/telemetry) "
            "to support evidencing usage/impact of the software. Disable for benchmarking runs"
        ),
    )

    # Enforce cuda_arch must be set, for consistency between +cuda and +rocm
    conflicts("cuda_arch=none", when="+cuda", msg="CUDA architecture is required")

    # Must have one of the +cuda or +rocm variant enabled (no CPU builds)
    requires(
        "+cuda",
        "+rocm",
        policy="one_of",
        msg="One of either +cuda or +rocm must be enabled",
    )

    # Direct dependencies of benchmark-flamegpu
    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("cmake@3.25.2:4.3", type="build")
    depends_on("git@1.6.6:", type="build")
    depends_on("nlohmann-json@3.11.3:")
    depends_on("cli11@2.5:")
    with when("+rocm"):
        depends_on("rocm-smi-lib")
    # Note: NVML is not a separate spack package

    # As of 2026-11, FLAMEGPU2 is not (yet) an independent spack package (it cannot be --installed)
    # instead specify relevant transitive dependencies (via depend_on or resource)
    # depends_on("flamegpu2", type="build")  # variants would need to match
    resource(
        name="flamegpu2",
        git="https://github.com/FLAMEGPU/FLAMEGPU2.git",
        tag="4fa74199ad0623642b51c9e49fad3884c23f5419",  # amdgpu support commit in master
        destination="spack-resources",
        placement="flamegpu2",
    )
    # CUDA >= 12.4 supported by FLAMEGPU 2.0.0-rc.6
    depends_on("cuda@12.4:", when="+cuda")
    # HIP/ROCM >= 7.0 supported by FLAMEGPU 2.0.0-rc.6
    depends_on("hip@7.0:", when="+rocm")
    # GPU-agnostic transitive dependencies from flamegpu2
    # depends_on("nlohmann-json@3.11.3:") # duplicate, commented out until separated.
    depends_on("tinyxml2@9.0.0:")
    depends_on("git", type="build")
    # CUDA only transitive dependencies from flamegpu2
    with when("+cuda"):
        # cccl is part of (relevant) CUDA versions, but also has a separate upstream spack package
        # However, the concretiser was failing with this dependency, so ignore for now
        # depends_on("cccl@3:")
        depends_on("nvtx@3:", when="+profiling")
        # jitify2 is not correctly versioned (always 0.9), requires patching & has no spack package
        # Instead, define as a resource so it is staged by spack
        resource(
            name="jitify",
            git="https://github.com/NVIDIA/jitify.git",
            commit="44e978b21fc8bdb6b2d7d8d179523c8350db72e5",
            destination="spack-resources",
            placement="jitify",
        )
    # ROCM only transivitve dependencies from flamegpu2
    with when("+rocm"):
        depends_on("rocm-core")
        depends_on("rocthrust")
        depends_on("hipcub")
        depends_on("hiprand")
        depends_on("rocprofiler-sdk", when="+profiling")

    # Define where the root CMakeLists.txt is within the benchmark-flamegpu repository
    root_cmakelists_dir = "."

    def setup_build_environment(self, env: EnvironmentModifications) -> None:
        # Various ROCm/HIP CMakeLists set -x hip or --offload-arch for cxx objects
        # This requires a hip-aware host compilers (i.e. hipcc or amdclang)
        if self.spec.satisfies("+rocm"):
            env.set("CC", self.spec["hip"].hipcc)
            env.set("CXX", self.spec["hip"].hipcc)

    def cmake_args(self):
        args = [
            # Always forward the value for seatbelts, defaults to ON in CMake
            self.define("FLAMEGPU_SEATBELTS", self.spec.variants["seatbelts"].value),
            # Always forward if profiling should be enabled value
            self.define("FLAMEGPU_ENABLE_PROFILING", self.spec.variants["profiling"].value),
            # Usage telemetry defaults to ON, so always specify a value (and suppress the notice)
            self.define("FLAMEGPU_SHARE_USAGE_STATISTICS", self.spec.variants["telemetry"].value),
            self.define("FLAMEGPU_TELEMETRY_SUPPRESS_NOTICE", "ON"),
            # configure this cmake to explicitly use spack-provided transitive dependencies.
            self.define("USE_SPACK_FLAMEGPU2_DEPS", "ON"),
            # Make fetch content not use the internet, enforcing offline builds
            self.define("FETCHCONTENT_FULLY_DISCONNECTED", True),
        ]

        # Define ROCm only cmake arguments
        if self.spec.satisfies("+rocm"):
            # Explicitly set amdclang++ as the hip compiler
            args.append(
                self.define(
                    "CMAKE_HIP_COMPILER",
                    os.path.join(self.spec["llvm-amdgpu"].prefix.bin, "amdclang++"),
                )
            )
            args.append(self.define("FLAMEGPU_BACKEND", "HIP"))
            args.append(
                self.define("CMAKE_HIP_ARCHITECTURES", self.spec.variants["amdgpu_target"].value)
            )

        # Define CUDA only cmake arguments
        if self.spec.satisfies("+cuda"):
            args.append(self.define("FLAMEGPU_BACKEND", "CUDA"))
            args.append(
                self.define("CMAKE_CUDA_ARCHITECTURES", self.spec.variants["cuda_arch"].value)
            )

        # Ensure the flamegpu2 spack-resource is used (prior to upstream spack package support)
        flamegpu_root = os.path.join(self.stage.source_path, "spack-resources", "flamegpu2")
        if os.path.exists(flamegpu_root):
            args.append(self.define("FLAMEGPU_ROOT", flamegpu_root))
        # Use the jitify spack-resource (for +cuda)
        if self.spec.satisfies("+cuda"):
            jitify_root = os.path.join(self.stage.source_path, "spack-resources", "jitify")
            if os.path.exists(jitify_root):
                args.append(self.define("FETCHCONTENT_SOURCE_DIR_JITIFY", jitify_root))

        return args
