# UKRI benchmark Spack packages

[![CI](https://github.com/ukri-bench/spack-packages/actions/workflows/ci.yml/badge.svg)](https://github.com/ukri-bench/spack-packages/actions/workflows/ci.yml)
[![Build bench-dolfinx](https://github.com/ukri-bench/spack-packages/actions/workflows/build-bench-dolfinx.yml/badge.svg)](https://github.com/ukri-bench/spack-packages/actions/workflows/build-bench-dolfinx.yml)
[![Build nemo](https://github.com/ukri-bench/spack-packages/actions/workflows/build-nemo.yml/badge.svg)](https://github.com/ukri-bench/spack-packages/actions/workflows/build-nemo.yml)

A [Spack](https://spack.io) package repository (namespace `ukri_bench`) for the
UKRI Living Benchmarks.

## Packages

- `bench-dolfinx`: the [DOLFINx benchmark](https://github.com/ukri-bench/benchmark-dolfinx).
  Versions: `0.10.0` (the default, built against DOLFINx 0.10) and `main`
  (built against DOLFINx 0.11). CPU by default; `+cuda
  cuda_arch=<arch>` or `+rocm amdgpu_target=<target>` for GPU builds (one of
  the two, with an architecture).
- `benchmark-flamegpu`: the [FLAMEGPU benchmark](https://github.com/ukri-bench/benchmark-flamegpu).
  Versions: `main` (built against FLAMEGPU `2.0.0-rc.6+4fa74199`). GPU only; `+cuda cuda_arch=<arch>` or `+rocm amdgpu_target=<target>` for GPU builds (one of the two, with an architecture).
- `fenics-dolfinx`: the builtin package with one added patch for DOLFINx
  0.11, without which nvcc 13 aborts with an internal error on the header
  `dolfinx/mesh/EntityMap.h`. It overrides the builtin package while this
  repository is added.
- `mesa`: the builtin package with the upstream patch that lets Mesa 24.3/25.0
  build against glibc 2.43 (e.g. Ubuntu 26.04), which declares the C23
  `call_once` in `<stdlib.h>`. Needed by ROCm builds (`hip` depends on
  `gl`). It overrides the builtin package while this repository is added.
- `nemo`: the [NEMO](https://www.nemo-ocean.eu/) ocean model (5.0.2 by
  default; also 5.0.1 and 5.0), with optional PSyclone OpenMP CPU/GPU
  transformations. The source configuration is selected with `config=`.
  Supported Fortran compilers: gcc, nvhpc, oneapi and cce. OpenMP variants:
  - `+openmp`: apply PSyclone's OpenMP CPU transformations;
  - `+openmp_offload` (with `+openmp`): apply the GPU offload transformations
    instead. The offload compiler/linker flags must be given with
    `openmp_flags=` (for example `openmp_flags="-mp=gpu -gpu=cc90"` with nvhpc);
  - `+reproducible` (nvhpc only): disable optimisations that change results
    between CPU and GPU runs.

  These variants were previously named `omp`, `omp_offload` and `omp_flags`.

`spack info <package>` lists all variants.

## Usage

Requires Spack v1.2 or later (Package API v2.5).

`bench-dolfinx@main` needs DOLFINx 0.11, which is in the builtin packages
([spack-packages](https://github.com/spack/spack-packages)) from
`releases/v2026.10`. Spack v1.2.2 uses `releases/v2026.06` by default, which
has only DOLFINx 0.10. To switch:

```console
spack repo update builtin --branch releases/v2026.10
```

Add the repository directly from GitHub:

```console
spack repo add https://github.com/ukri-bench/spack-packages.git
```

or from a local clone:

```console
git clone https://github.com/ukri-bench/spack-packages.git
spack repo add spack-packages/spack_pkgs/spack_repo/ukri_bench
```

Then, for example:

```console
spack install bench-dolfinx
spack install bench-dolfinx +cuda cuda_arch=90
spack install benchmark-flamegpu +cuda cuda_arch=90
spack install benchmark-flamegpu +rocm amdgpu_target=gfx942
spack install nemo config=BENCH
spack install nemo +openmp %fortran=gcc
spack install nemo +openmp +openmp_offload openmp_flags="-mp=gpu -gpu=cc90" %fortran=nvhpc
```

### Running

- `bench-dolfinx` installs the executable `bench_dolfinx` (`bench_dolfinx -h`
  lists options). `--qmode` defaults to 0 for CPU builds, which support
  only `--qmode=0`, and to 1 for GPU builds. For example:

  ```console
  mpiexec -n 2 bench_dolfinx --ndofs=10000 --degree=3 --nreps=10
  ```
- `benchmark-flamegpu` installs the executable `benchmark-flamegpu` (`benchmark-flamegpu -h` lists options).

- `nemo` installs the build configuration under its prefix, with the
  executable at `<prefix>/EXP00/nemo`, and a `nemo-wrapper` script that
  prepares a run directory from the reference experiment (`nemo-wrapper
  --help`). The wrapper does not run NEMO, and will only replace a run
  directory it created itself.

## Development

See [AGENTS.md](AGENTS.md) for repository conventions, local checks and how to
add a package.

Python style is checked with [ruff](https://docs.astral.sh/ruff/)
(`ruff check .` and `ruff format --check .`). GitHub Actions workflows:

- [`ci.yml`](.github/workflows/ci.yml): ruff, then `spack audit` and
  `spack spec` for several variants of each package, against the pinned
  spack-packages commit.
- [`build-bench-dolfinx.yml`](.github/workflows/build-bench-dolfinx.yml) and
  [`build-nemo.yml`](.github/workflows/build-nemo.yml): build each package
  on Ubuntu and AlmaLinux (target `x86_64_v3`) with a pinned Spack release and
  [spack-packages](https://github.com/spack/spack-packages) commit, then
  check and smoke-test it. The OS releases are set in
  [`build-package.yml`](.github/workflows/build-package.yml) and the pins in
  [`.github/spack/versions.env`](.github/spack/versions.env). bench-dolfinx
  is also built for CUDA and ROCm, at the versions pinned in
  [`.github/spack/packages.yaml`](.github/spack/packages.yaml); the runners
  have no GPU, so those builds are compile-only. The workflows run on changes to the package, weekly, and
  on demand.

Dependencies for the build workflows come from a Spack OCI build cache at
`ghcr.io/ukri-bench/spack-packages-buildcache` (configured in
[`.github/spack/ci-env.yaml`](.github/spack/ci-env.yaml)). Each dependency
built from source is pushed as soon as it is installed, so progress is kept if
a build fails or is cancelled; the packages themselves are always built from
source and are not cached. The cache is visible to members of the `ukri-bench`
organization only; pull requests from forks build without pushing to it.

## License

MIT; see [LICENSE](LICENSE).
