import os
import sys
import textwrap
from pathlib import Path
from spack.package import *


class Nemo(Package):
    """
    The 'Nucleus for European Modelling of the Ocean' (NEMO) is a
    state-of-the-art modelling framework. It is used for research
    activities and forecasting services in ocean and climate sciences.
    """

    homepage = "https://www.nemo-ocean.eu/"
    git = "https://forge.nemo-ocean.eu/nemo/nemo.git"
    version("5.0", commit="bc25452d80459627cb1d1ee9e6a128d7932d6e1b")
    maintainers("addy419")

    phases = ("configure", "build", "install")

    # --- Representative configs ---
    nmconfigs = {
        "ORCA2_ICE_PISCES": {"ice": True, "pisces": True},
        "BENCH": {"ice": True, "pisces": True},
        "GOSI10p0.0_like_eORCA1": {"ice": True, "pisces": False},
        "GOSI10p0.0_like_eORCA025": {"ice": True, "pisces": False},
        "GOSI10p0.0_like_eORCA12": {"ice": True, "pisces": False},
        "GENERIC": {"ice": True, "pisces": True},
    }

    # --- Variants ---
    variant("mpi", default=True, description="Enable MPI support")
    variant(
        "ice",
        default=False,
        description="""Enable SEA-ICE
        In polar regions temperatures become cold enough for seawater to freeze and sea ice forms on the surface of the ocean. NEMO includes a sea-ice model component, known as SI³ (Sea Ice modelling Integrated Initiative), which runs along with the ocean component with a different set of equations.""",
    )
    variant(
        "pisces",
        default=False,
        description="""Enable PISCES
        PISCES is a biogeochemical model that simulates marine biological productivity and describes the biogeochemical cycles of carbon, oxygen and of the main nutrients (P, N, Si, Fe) (Aumont et al., 2015).""",
    )
    variant("xios", default=False, description="Enable XIOS IO server support")
    variant(
        "openmp",
        default=False,
        description="Apply OpenMP transforms to NEMO through PSyclone",
    )
    # TODO: Add GPU support
    # variant('openmp-offload', default=False, description='Apply OpenMP GPU transforms to NEMO through PSyclone')
    variant(
        "config",
        default="ORCA2_ICE_PISCES",
        values=(tuple(nmconfigs.keys())),
        multi=False,
        description="Build the specified NEMO source configuration",
    )
    variant(
        "generic_config",
        default="none",
        values=str,
        description="Specify the generic configuration to use",
    )

    # --- Conflicts ---
    conflicts(
        "+xios", msg="The XIOS spack package is currently broken and cannot be used"
    )
    conflicts(
        "+openmp",
        msg="The py-psyclone package is currently broken with spackv0.23.1, change if newer versions work",
    )
    conflicts(
        "config=GENERIC",
        when="generic_config=none",
        msg="generic_config should be set when using config=GENERIC",
    )

    for key, value in nmconfigs.items():
        if value["ice"] == False:
            conflicts(
                "+ice",
                when=f"config={key}",
                msg=f"{key} does not support SEA-ICE. Use config=GENERIC to circumvent this",
            )
        if value["pisces"] == False:
            conflicts(
                "+pisces",
                when=f"config={key}",
                msg=f"{key} does not support PISCES. Use config=GENERIC to circumvent this",
            )

    # --- Compilers ---
    depends_on("c", type="build")
    depends_on("fortran", type="build")

    # --- Dependencies ---
    depends_on("binutils", type="build")
    depends_on("gmake", type="build")
    # nemo segfaults without mpi even if we aren't using it
    depends_on("mpi", type="build")
    depends_on("hdf5 +shared +fortran +mpi", type="build")
    depends_on("xios@2.5:", type=("build", "link"), when="+xios")
    depends_on("netcdf-c@4.9.0: +mpi +shared", type=("build", "link"))
    depends_on("netcdf-fortran@4.6.1: +shared", type="build")
    depends_on("py-f90nml", type="run")
    depends_on("py-psyclone", type="build", when="+openmp")

    # --- Patches ---
    patch("makenemo.patch")
    patch("sct_psyclone.patch")

    # --- Variables ---
    config_name = "BLDCFG"
    source_cfg = None
    source_path = None
    config_path = None
    add_keys = []
    del_keys = []

    @run_before("build")
    def set_config_paths(self):
        nemo_root = self.stage.source_path
        self.source_cfg = self.spec.variants["config"].value
        if self.source_cfg == "GENERIC":
            self.source_cfg = self.spec.variants["generic_config"].value

        cfgs = Path(join_path(nemo_root, "cfgs", self.source_cfg))
        tests = Path(join_path(nemo_root, "tests", self.source_cfg))

        if cfgs.is_dir():
            self.source_path = cfgs
        elif tests.is_dir():
            self.source_path = tests
        else:
            raise InstallError(
                f"Configuration failed: Cannot find source configuration {self.source_cfg}"
            )

        self.config_path = Path(join_path(self.source_path.parent, self.config_name))

    def setup_build_environment(self, env):
        if self.spec.satisfies("+xios"):
            env.set("XIOS_PATH", self.spec["xios"].prefix)
        if self.spec.satisfies("+openmp"):
            utilspath = join_path(
                self.spec["py-psyclone"].prefix.share,
                "psyclone",
                "examples",
                "nemo",
                "scripts",
            )
            env.prepend_path("PYTHONPATH", utilspath)

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

        if spec.satisfies("+xios"):
            xiosdir = str(spec["xios"].prefix)

        if spec.satisfies("+openmp"):
            psydir = str(spec["py-psyclone"].prefix)

        # TODO: Add -march, check how spack does it

        if spec.satisfies("%gcc"):
            fflags = "-fdefault-real-8 -O2 -funroll-all-loops -fcray-pointer -ffree-line-length-none"
            ldflags = "-fdefault-real-8"
            if spec.satisfies("+openmp"):
                fflags += " -fopenmp"
                ldflags += " -fopenmp"
        elif spec.satisfies("%nvhpc"):
            fflags = "-i4 -Mr8 -Mnovect -Mflushz -Minline -Mnofma -O2 -gopt -traceback"
            ldflags = "-i4 -Mr8 -Mnofma"
            if spec.satisfies("+openmp"):
                fflags += " -mp"
                ldflags += " -mp"
        elif spec.satisfies("%oneapi"):
            fflags = "-i4 -r8 -O2 -fp-model strict -xHost -fno-alias"
            ldflags = "-i4 -r8"
            if spec.satisfies("+openmp"):
                fflags += " -fiopenmp"
                ldflags += " -fiopenmp"
        elif spec.satisfies("%cce"):
            fflags = "-em -s integer32 -s real64 -O2 -hvector_classic -hflex_mp=intolerant -N1023 -M878"
            ldflags = ""
            arch_extra = "bld::tool::fc_modsearch -J"
            if spec.satisfies("+openmp"):
                fflags += " -h omp"
                ldflags += " -h omp"

        arch = textwrap.dedent(
            f"""
            %NCDFF_HOME          {nfdir}
            %NCDFC_HOME          {ncdir}
            %HDF5_HOME           {h5dir}
            %XIOS_HOME           {xiosdir}
            %PSYCLONE_HOME       {psydir}
            
            %NCDF_INC            -I%NCDFF_HOME/include
            %NCDF_LIB            -L%NCDFF_HOME/lib -lnetcdff -L%NCDFC_HOME/lib -lnetcdf -L%HDF5_HOME/lib -lhdf5_hl -lhdf5 -lhdf5
            %XIOS_INC            -I%XIOS_HOME/inc
            %XIOS_LIB            -L%XIOS_HOME/lib -lxios -lstdc++
            %CPP	             cpp -Dkey_nosignedzero
            %FC                  {fcompiler}
            %PROD_FCFLAGS        {fflags}
            %DEBUG_FCFLAGS       
            %FFLAGS
            %LD                  {fcompiler}
            %LDFLAGS             {ldflags} -Wl,-rpath=%HDF5_HOME/lib -Wl,-rpath=%NCDFF_HOME/lib -Wl,-rpath=%XIOS_HOME/lib
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

        if spec.satisfies("+xios"):
            self.add_keys.append("key_iomput")
            if spec["xios"].version.satisfies("@3.0:"):
                self.del_keys.append("key_xios")
                self.add_keys.append("key_xios3")
            elif spec["xios"].version.satisfies("@2.5:"):
                self.del_keys.append("key_xios3")
                self.add_keys.append("key_xios")
        else:
            self.del_keys.append("key_xios")
            self.del_keys.append("key_xios3")
            self.del_keys.append("key_iomput")

        if spec.satisfies("+mpi"):
            if spec.satisfies("@4.2:"):
                self.del_keys.append("key_mpi_off")
            elif spec.satisfies("@=4.0:"):
                self.add_keys.append("key_mpp_mpi")
        else:
            if spec.satisfies("@4.2:"):
                self.add_keys.append("key_mpi_off")
            elif spec.satisfies("@=4.0:"):
                self.del_keys.append("key_mpp_mpi")

        # TODO:
        # if spec.satisfies("%nvhpc"):
        #    self.add_keys.append("key_nosignedzero")

        if spec.satisfies("+ice"):
            self.add_keys.append("key_si3")
        else:
            self.del_keys.append("key_si3")

        if spec.satisfies("+pisces"):
            self.add_keys.append("key_top")
        else:
            self.del_keys.append("key_top")

    def build(self, spec, prefix):
        params = []

        params.append("-j")
        params.append(f"{make_jobs}")
        params.append("-m")
        params.append(f"fort")

        if self.spec.satisfies("+openmp"):
            trans = join_path(
                self.spec["py-psyclone"].prefix.share,
                "psyclone",
                "examples",
                "nemo",
                "scripts",
                "omp_cpu_trans.py",
            )
            params.append("-p")
            params.append(trans)

        if self.config_path.parent.name == "cfgs":
            params.append("-r")
        elif self.config_path.parent.name == "tests":
            params.append("-a")
        params.append(self.source_cfg)
        params.append("-n")
        params.append(self.config_name)

        if self.del_keys:
            params.append("del_key")
            params.append(" ".join(self.del_keys))
        if self.add_keys:
            params.append("add_key")
            params.append(" ".join(self.add_keys))

        with working_dir(self.stage.source_path):
            makenemo = Executable(join_path(".", "makenemo"))
            makenemo(*params)

        if spec.satisfies("+xios"):
            xios_exe = join_path(self.spec["xios"].prefix.bin, "xios_server.exe")
            xios_run_exe = join_path(self.config_path, "EXP00", "xios_server.exe")
            if not os.path.exists(xios_run_exe):
                os.symlink(xios_exe, xios_run_exe)

    def install(self, spec, prefix):
        params = []
        params.append(join_path(self.package_dir, "create_wrapper.py"))
        params.append("--prefix=" + prefix)

        if spec.satisfies("+xios"):
            params.append("--xios")
        if spec.satisfies("+mpi"):
            params.append("--mpi")

        python = Executable("python3")
        python(*params)

        install_tree(str(self.config_path), prefix, symlinks=False)
