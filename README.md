# UKRI benchmark Spack packages

[![CI](https://github.com/ukri-bench/spack-packages/actions/workflows/ci.yml/badge.svg)](https://github.com/ukri-bench/spack-packages/actions/workflows/ci.yml)
[![Build bench-dolfinx](https://github.com/ukri-bench/spack-packages/actions/workflows/build-bench-dolfinx.yml/badge.svg)](https://github.com/ukri-bench/spack-packages/actions/workflows/build-bench-dolfinx.yml)
[![Build nemo](https://github.com/ukri-bench/spack-packages/actions/workflows/build-nemo.yml/badge.svg)](https://github.com/ukri-bench/spack-packages/actions/workflows/build-nemo.yml)

A [Spack](https://spack.io) package repository (namespace `ukri_bench`) for the
UKRI Living Benchmarks.

## Packages

- `bench-dolfinx`: the [DOLFINx benchmark](https://github.com/ukri-bench/benchmark-dolfinx)
  (version `main`), built against DOLFINx 0.11. CPU by default; `+cuda
  cuda_arch=<arch>` or `+rocm amdgpu_target=<target>` for GPU builds (one of
  the two, with an architecture).
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

Requires Spack v1.0 or later (Package API v2.0).

`bench-dolfinx` needs DOLFINx 0.11, which is in the builtin packages
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
spack install nemo config=BENCH
spack install nemo +openmp %fortran=gcc
spack install nemo +openmp +openmp_offload openmp_flags="-mp=gpu -gpu=cc90" %fortran=nvhpc
```

### Running

- `bench-dolfinx` installs the executable `bench_dolfinx` (`bench_dolfinx -h`
  lists options). CPU builds support only `--qmode=0`; the default
  `--qmode=1` is GPU-only. For example:

  ```console
  mpiexec -n 2 bench_dolfinx --ndofs=10000 --degree=3 --nreps=10 --qmode=0
  ```

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
  [`build-nemo.yml`](.github/workflows/build-nemo.yml): build each package in
  an `ubuntu:26.04` container (target `x86_64_v3`) with a pinned Spack release
  and [spack-packages](https://github.com/spack/spack-packages) commit (set in
  [`.github/spack/versions.env`](.github/spack/versions.env)), then run a
  smoke test. They run on changes to the package, weekly, and on demand.

Dependencies for the build workflows come from a Spack OCI build cache at
`ghcr.io/ukri-bench/spack-packages-buildcache` (configured in
[`.github/spack/ci-env.yaml`](.github/spack/ci-env.yaml)). Each dependency
built from source is pushed as soon as it is installed, so progress is kept if
a build fails or is cancelled; the packages themselves are always built from
source and are not cached. The cache is visible to members of the `ukri-bench`
organization only; pull requests from forks build without pushing to it.

## License

MIT; see [LICENSE](LICENSE).
