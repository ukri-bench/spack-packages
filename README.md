# UKRI benchmark Spack packages

A [Spack](https://spack.io) package repository (namespace `ukri_bench`) for the
UKRI Living Benchmarks.

## Packages

- `bench-dolfinx`: [DOLFINx](https://github.com/FEniCS/dolfinx) benchmark
  (CPU, CUDA and ROCm).
- `nemo`: [NEMO](https://www.nemo-ocean.eu/) ocean model, with optional
  PSyclone OpenMP/GPU transformations.

## Usage

Requires Spack v1.0 or later (Package API v2.0).

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
spack info bench-dolfinx
spack install bench-dolfinx +cuda cuda_arch=90
spack install nemo config=BENCH
```

After installing `nemo`, `nemo-wrapper --help` describes how to prepare a run
directory.

## Development

Python style is checked with [ruff](https://docs.astral.sh/ruff/)
(`ruff check .`). GitHub Actions workflows:

- [`ci.yml`](.github/workflows/ci.yml): ruff, and `spack audit`/`spack spec`
  against a pinned Spack release.
- [`build-bench-dolfinx.yml`](.github/workflows/build-bench-dolfinx.yml) and
  [`build-nemo.yml`](.github/workflows/build-nemo.yml): build each package
  with a pinned Spack release and
  [spack-packages](https://github.com/spack/spack-packages) commit (set in
  [`build-package.yml`](.github/workflows/build-package.yml)), then run a
  smoke test. They run on changes to the package, weekly, and on demand.
  Dependencies are taken from and pushed to a Spack OCI build cache at
  `ghcr.io/ukri-bench/spack-packages-buildcache` (configured in
  [`.github/spack/ci-env.yaml`](.github/spack/ci-env.yaml)). Each dependency
  built from source is pushed as soon as it is installed, so progress is kept
  if a build fails or is cancelled; the package itself is always built from
  source.
