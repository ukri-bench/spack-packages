# Copyright 2025 Aditya Sadawarte
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import sys
import textwrap
from pathlib import Path

from spack_repo.builtin.build_systems.generic import Package

from spack.package import *


class Nemo(Package):
    """The 'Nucleus for European Modelling of the Ocean' (NEMO) is a
    state-of-the-art modelling framework. It is used for research
    activities and forecasting services in ocean and climate sciences.
    """

    homepage = "https://www.nemo-ocean.eu/"
    git = "https://forge.nemo-ocean.eu/nemo/nemo.git"

    maintainers("addy419")

    version("5.0", commit="bc25452d80459627cb1d1ee9e6a128d7932d6e1b")

    phases = ("configure", "build", "install")

    # Representative source configurations and the optional components they support
    nmconfigs = {
        "ORCA2_ICE_PISCES": {"ice": True, "pisces": True},
        "BENCH": {"ice": True, "pisces": True},
        "GOSI10p0.0_like_eORCA1": {"ice": True, "pisces": False},
        "GOSI10p0.0_like_eORCA025": {"ice": True, "pisces": False},
        "GOSI10p0.0_like_eORCA12": {"ice": True, "pisces": False},
        "GENERIC": {"ice": True, "pisces": True},
    }

    # Name of the NEMO build configuration directory created by makenemo
    config_name = "BLDCFG"

    # --- Variants ---
    variant("mpi", default=True, description="Enable MPI support")
    variant("ice", default=False, description="Enable the SI3 sea-ice model component")
    variant("pisces", default=False, description="Enable the PISCES biogeochemical model")
    variant("xios", default=False, description="Enable XIOS IO server support")
    variant("omp", default=False, description="Apply OpenMP transforms to NEMO through PSyclone")
    variant(
        "omp_offload",
        default=False,
        when="+omp",
        description="Enable OpenMP offloading to the GPU",
    )
    variant(
        "omp_flags",
        values=str,
        default="none",
        when="+omp_offload",
        description="Compiler and linker flags for OpenMP offloading (required with omp_offload)",
    )
    # TODO: Add non-nvhpc support for reproducibility
    variant(
        "reproducible",
        default=False,
        description="Disable optimisations to generate reproducible results on CPU and GPU",
        when="%nvhpc",
    )
    variant(
        "config",
        default="ORCA2_ICE_PISCES",
        values=tuple(nmconfigs.keys()),
        multi=False,
        description="Build the specified NEMO source configuration",
    )
    variant(
        "generic_config",
        default="none",
        values=str,
        when="config=GENERIC",
        description="Name of the source configuration (under cfgs/ or tests/) to build",
    )

    # --- Conflicts ---
    conflicts("+xios", msg="The XIOS spack package is currently broken and cannot be used")
    conflicts(
        "generic_config=none",
        when="config=GENERIC",
        msg="generic_config must be set when using config=GENERIC",
    )
    conflicts(
        "omp_flags=none",
        when="+omp_offload",
        msg="OpenMP offload flags must be specified by omp_flags when omp_offload is enabled",
    )

    for _cfg, _features in nmconfigs.items():
        if not _features["ice"]:
            conflicts(
                "+ice",
                when=f"config={_cfg}",
                msg=f"{_cfg} does not support SEA-ICE. Use config=GENERIC to circumvent this",
            )
        if not _features["pisces"]:
            conflicts(
                "+pisces",
                when=f"config={_cfg}",
                msg=f"{_cfg} does not support PISCES. Use config=GENERIC to circumvent this",
            )
    del _cfg, _features

    # --- Compilers ---
    depends_on("c", type="build")
    depends_on("fortran", type="build")

    # --- Dependencies ---
    depends_on("binutils", type="build")
    depends_on("gmake", type="build")
    # NEMO segfaults without MPI even if we aren't using it
    depends_on("mpi")
    depends_on("hdf5 +shared +fortran +mpi")
    depends_on("xios@2.5:", when="+xios")
    depends_on("netcdf-c@4.9.0: +mpi +shared")
    depends_on("netcdf-fortran@4.6.1: +shared")
    depends_on("py-f90nml", type="run")
    depends_on("py-psyclone", type="build", when="+omp")

    @property
    def source_cfg(self):
        """Name of the NEMO source configuration to build."""
        if self.spec.satisfies("config=GENERIC"):
            return self.spec.variants["generic_config"].value
        return self.spec.variants["config"].value

    @property
    def source_cfg_dir(self):
        """Directory of the source configuration (under cfgs/ or tests/)."""
        nemo_root = Path(self.stage.source_path)
        for parent in ("cfgs", "tests"):
            path = nemo_root / parent / self.source_cfg
            if path.is_dir():
                return path
        raise InstallError(
            f"Configuration failed: Cannot find source configuration {self.source_cfg}"
        )

    @property
    def config_path(self):
        """Build configuration directory created by makenemo."""
        return self.source_cfg_dir.parent / self.config_name

    def nemo_keys(self):
        """Return the CPP keys to add and delete for this spec."""
        spec = self.spec
        add_keys = []
        del_keys = []

        if spec.satisfies("+xios"):
            add_keys.append("key_iomput")
            if spec.satisfies("^xios@3.0:"):
                del_keys.append("key_xios")
                add_keys.append("key_xios3")
            else:
                del_keys.append("key_xios3")
                add_keys.append("key_xios")
        else:
            del_keys.extend(["key_xios", "key_xios3", "key_iomput"])

        if spec.satisfies("@4.2:"):
            (del_keys if spec.satisfies("+mpi") else add_keys).append("key_mpi_off")
        elif spec.satisfies("@4.0:4.1"):
            (add_keys if spec.satisfies("+mpi") else del_keys).append("key_mpp_mpi")

        # TODO:
        # if spec.satisfies("%nvhpc"):
        #    add_keys.append("key_nosignedzero")

        (add_keys if spec.satisfies("+ice") else del_keys).append("key_si3")
        (add_keys if spec.satisfies("+pisces") else del_keys).append("key_top")

        return add_keys, del_keys

    def setup_build_environment(self, env):
        spec = self.spec
        if spec.satisfies("+xios"):
            env.set("XIOS_PATH", spec["xios"].prefix)
        if spec.satisfies("+omp"):
            scripts_dir = join_path(
                spec["py-psyclone"].prefix.share, "psyclone", "examples", "nemo", "scripts"
            )
            env.prepend_path("PYTHONPATH", scripts_dir)
            env.set("PSYCLONE_COMPILER", spec["mpi"].mpifc)
            if spec.satisfies("+omp_offload"):
                trans = join_path(scripts_dir, "omp_gpu_trans.py")
                if spec.satisfies("+reproducible"):
                    env.set("REPRODUCIBLE", "True")  # only supported on Nvidia GPUs
            else:
                trans = join_path(scripts_dir, "omp_cpu_trans.py")
            env.set("PSYCLONE_OPTS", f"-l output -s {trans}")

    def configure(self, spec, prefix):
        ar = join_path(spec["binutils"].prefix.bin, "ar")
        gmake = join_path(spec["gmake"].prefix.bin, "gmake")
        fcompiler = spec["mpi"].mpifc
        h5dir = spec["hdf5"].prefix
        ncdir = spec["netcdf-c"].prefix
        nfdir = spec["netcdf-fortran"].prefix
        xiosdir = ""
        psydir = ""
        arch_extra = ""
        ldflags = ""

        if spec.satisfies("+omp"):
            psydir = spec["py-psyclone"].prefix
            fcompiler = join_path(spec["py-psyclone"].prefix.bin, "psyclonefc")

        if spec.satisfies("%fortran=gcc"):
            fflags = (
                "-fdefault-real-8 -O2 -funroll-all-loops -fcray-pointer -ffree-line-length-none"
            )
        elif spec.satisfies("%fortran=nvhpc"):
            fflags = "-i4 -Mr8 -Minline"
            if spec.satisfies("+reproducible"):
                fflags += " -O2 -Mnovect -Mflushz -Mnofma"
            else:
                fflags += " -O3"
        elif spec.satisfies("%fortran=oneapi"):
            fflags = "-i4 -r8 -O2 -fp-model strict -xHost -fno-alias"
        elif spec.satisfies("%fortran=cce"):
            fflags = (
                "-em -s integer32 -s real64 -O2 -hvector_classic -hflex_mp=intolerant -N1023 -M878"
            )
            arch_extra = "bld::tool::fc_modsearch -J"
        else:
            raise InstallError(
                f"Unsupported Fortran compiler {spec['fortran'].name}: "
                "supported compilers are gcc, nvhpc, oneapi and cce"
            )

        if spec.satisfies("+omp~omp_offload"):
            openmp_flag = self.compiler.openmp_flag
            fflags += f" {openmp_flag}"
            ldflags += f" {openmp_flag}"
        elif spec.satisfies("+omp+omp_offload"):
            offload_flags = spec.variants["omp_flags"].value
            fflags += f" {offload_flags}"
            ldflags += f" {offload_flags}"
            if spec.satisfies("+reproducible"):
                fflags += " -gpu=math_uniform"
                ldflags += " -gpu=math_uniform"

        rpath_dirs = [
            spec["hdf5"].libs.directories[0],
            spec["netcdf-c"].libs.directories[0],
            spec["netcdf-fortran"].libs.directories[0],
        ]
        xios_inc = ""
        xios_lib = ""
        if spec.satisfies("+xios"):
            xiosdir = spec["xios"].prefix
            xios_inc = "-I%XIOS_HOME/inc"
            xios_lib = "-L%XIOS_HOME/lib -lxios -lstdc++"
            rpath_dirs.append(spec["xios"].prefix.lib)
        ldflags += "".join(f" -Wl,-rpath,{d}" for d in rpath_dirs)

        ncdf_lib = " ".join(
            [
                spec["netcdf-fortran"].libs.ld_flags,
                spec["netcdf-c"].libs.ld_flags,
                f"-L{spec['hdf5'].libs.directories[0]} -lhdf5_hl -lhdf5",
            ]
        )

        arch = textwrap.dedent(
            f"""\
            %NCDFF_HOME          {nfdir}
            %NCDFC_HOME          {ncdir}
            %HDF5_HOME           {h5dir}
            %XIOS_HOME           {xiosdir}
            %PSYCLONE_HOME       {psydir}

            %NCDF_INC            -I%NCDFF_HOME/include
            %NCDF_LIB            {ncdf_lib}
            %XIOS_INC            {xios_inc}
            %XIOS_LIB            {xios_lib}
            %CPP                 cpp -Dkey_nosignedzero
            %FC                  {fcompiler}
            %PROD_FCFLAGS        {fflags}
            %DEBUG_FCFLAGS
            %FFLAGS
            %LD                  {fcompiler}
            %LDFLAGS             {ldflags}
            %FPPFLAGS            -P -traditional
            %AR                  {ar}
            %ARFLAGS             -rs
            %MK                  {gmake}
            %USER_INC            %XIOS_INC %NCDF_INC
            %USER_LIB            %XIOS_LIB %NCDF_LIB
            {arch_extra}
            """
        )

        arch_fcm = join_path(self.stage.source_path, "arch", "arch-fort.fcm")
        with open(arch_fcm, "w") as f:
            f.write(arch)

    def build(self, spec, prefix):
        params = ["-j", str(make_jobs), "-m", "fort"]

        if self.source_cfg_dir.parent.name == "cfgs":
            params.append("-r")
        else:
            params.append("-a")
        params.extend([self.source_cfg, "-n", self.config_name])

        add_keys, del_keys = self.nemo_keys()
        if del_keys:
            params.extend(["del_key", " ".join(del_keys)])
        if add_keys:
            params.extend(["add_key", " ".join(add_keys)])

        with working_dir(self.stage.source_path):
            makenemo = Executable("./makenemo")
            makenemo(*params)

        if spec.satisfies("+xios"):
            xios_exe = join_path(spec["xios"].prefix.bin, "xios_server.exe")
            xios_run_exe = join_path(self.config_path, "EXP00", "xios_server.exe")
            if not os.path.exists(xios_run_exe):
                os.symlink(xios_exe, xios_run_exe)

    def install(self, spec, prefix):
        # Generate the run-directory wrapper script using Spack's own interpreter
        params = [join_path(self.package_dir, "create_wrapper.py"), f"--prefix={prefix}"]
        if spec.satisfies("+xios"):
            params.append("--xios")
        if spec.satisfies("+mpi"):
            params.append("--mpi")

        python = Executable(sys.executable)
        python(*params)

        install_tree(str(self.config_path), prefix, symlinks=False)
