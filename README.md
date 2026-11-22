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
(`ruff check .`). CI also audits and concretizes the packages against a pinned
Spack release; see [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
