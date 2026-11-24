# Copyright 2025 Aditya Sadawarte
#
# SPDX-License-Identifier: MIT

import os
import textwrap
from pathlib import Path

from spack.package import *


class Nemo(Package):
    """The 'Nucleus for European Modelling of the Ocean' (NEMO) is a
    state-of-the-art modelling framework. It is used for research
    activities and forecasting services in ocean and climate sciences.
    """

    homepage = "https://www.nemo-ocean.eu/"
    git = "https://forge.nemo-ocean.eu/nemo/nemo.git"

    maintainers("addy419")

    license("CECILL-2.0")

    version("5.0.2", tag="5.0.2", commit="dcc7fb8c1779fa8409e41e4ce3ab7d45b9ceb796")
    version("5.0.1", tag="5.0.1", commit="6f645ba8c1d97fb6c73c4deb3760148f5c5d1b9d")
    version("5.0", tag="5.0", commit="d6c9fd7692b7bc054875bd8d267ab4ac53d2d83c")

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
    variant("openmp", default=False, description="Apply PSyclone OpenMP transformations to NEMO")
    variant(
        "openmp_offload",
        default=False,
        when="+openmp",
        description="Enable OpenMP offloading to the GPU",
    )
    variant(
        "openmp_flags",
        values=str,
        default="none",
        when="+openmp_offload",
        description="OpenMP offload compiler and linker flags (required with openmp_offload)",
    )
    # TODO: Add non-nvhpc support for reproducibility
    variant(
        "reproducible",
        default=False,
        description="Disable optimisations to generate reproducible results on CPU and GPU",
        when="%fortran=nvhpc",
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
        "openmp_flags=none",
        when="+openmp_offload",
        msg="openmp_flags must be set when openmp_offload is enabled",
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
    requires(
        "%fortran=gcc",
        "%fortran=nvhpc",
        "%fortran=oneapi",
        "%fortran=cce",
        policy="one_of",
        msg="Supported Fortran compilers are gcc, nvhpc, oneapi and cce",
    )

    # --- Dependencies ---
    depends_on("gmake", type="build")
    # makenemo uses the Perl-based FCM build system; `fcm build` needs the URI module
    depends_on("perl", type="build")
    depends_on("perl-uri", type="build")
    # NEMO segfaults without MPI even if we aren't using it
    depends_on("mpi")
    depends_on("hdf5 +shared +fortran +mpi")
    depends_on("xios@2.5:", when="+xios")
    depends_on("netcdf-c@4.9.0: +mpi +shared")
    depends_on("netcdf-fortran@4.6.1: +shared")
    depends_on("py-f90nml", type="run")
    # psyclonefc was introduced in PSyclone 3.2. Builtin repos without a 3.2+ release
    # (e.g. releases/v2026.06, used by Spack v1.2) fall back to @master.
    depends_on("py-psyclone@3.2:", type="build", when="+openmp")

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

        (del_keys if spec.satisfies("+mpi") else add_keys).append("key_mpi_off")

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
        if spec.satisfies("+openmp"):
            scripts_dir = join_path(
                spec["py-psyclone"].prefix.share, "psyclone", "examples", "nemo", "scripts"
            )
            env.prepend_path("PYTHONPATH", scripts_dir)
            env.set("PSYCLONE_COMPILER", spec["mpi"].mpifc)
            if spec.satisfies("+openmp_offload"):
                trans = join_path(scripts_dir, "omp_gpu_trans.py")
                if spec.satisfies("+reproducible"):
                    env.set("REPRODUCIBLE", "True")  # only supported on Nvidia GPUs
            else:
                trans = join_path(scripts_dir, "omp_cpu_trans.py")
            env.set("PSYCLONE_OPTS", f"-l output -s {trans}")

    def configure(self, spec, prefix):
        ar = which("ar", required=True).path
        gmake = join_path(spec["gmake"].prefix.bin, "gmake")
        fcompiler = spec["mpi"].mpifc
        nfdir = spec["netcdf-fortran"].prefix
        xiosdir = ""
        psydir = ""
        arch_extra = ""
        ldflags = ""

        if spec.satisfies("+openmp"):
            psydir = spec["py-psyclone"].prefix
            fcompiler = join_path(psydir.bin, "psyclonefc")

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

        if spec.satisfies("+openmp~openmp_offload"):
            openmp_flag = spec["fortran"].package.openmp_flag
            fflags += f" {openmp_flag}"
            ldflags += f" {openmp_flag}"
        elif spec.satisfies("+openmp+openmp_offload"):
            offload_flags = spec.variants["openmp_flags"].value
            fflags += f" {offload_flags}"
            ldflags += f" {offload_flags}"
            if spec.satisfies("+reproducible"):
                fflags += " -gpu=math_uniform"
                ldflags += " -gpu=math_uniform"

        xios_inc = ""
        xios_lib = ""
        if spec.satisfies("+xios"):
            xiosdir = spec["xios"].prefix
            xios_inc = "-I%XIOS_HOME/inc"
            xios_lib = f"{spec['xios'].libs.ld_flags} -lstdc++"

        # Link deps are RPATHed by Spack's compiler wrapper (used via the MPI wrappers)
        ncdf_lib = (
            spec["netcdf-fortran"].libs + spec["netcdf-c"].libs + spec["hdf5:hl"].libs
        ).ld_flags

        # FCM preprocesses with the system cpp (traditional mode), which is not a Spack dependency
        arch = textwrap.dedent(
            f"""\
            %NCDFF_HOME          {nfdir}
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
        install_tree(str(self.config_path), prefix, symlinks=False)

        # Run-directory wrapper script
        wrapper = join_path(prefix.bin, "nemo-wrapper")
        mkdirp(prefix.bin)
        install(join_path(self.package_dir, "nemo-wrapper.sh"), wrapper)
        filter_file("@PREFIX@", prefix, wrapper, string=True)
        filter_file("@MPI@", "true" if spec.satisfies("+mpi") else "false", wrapper, string=True)
        filter_file("@XIOS@", "true" if spec.satisfies("+xios") else "false", wrapper, string=True)
        set_executable(wrapper)
