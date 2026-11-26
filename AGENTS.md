# AGENTS.md

Guidance for coding agents (and humans) working in this repository.

## What this is

A [Spack](https://spack.io) package repository, namespace `ukri_bench`, for
the UKRI Living Benchmarks. It targets Spack v1.2+ and Package API v2.5
(`spack_pkgs/spack_repo/ukri_bench/repo.yaml`).

```text
spack-repo-index.yaml              # lets `spack repo add <git url>` find the repo
spack_pkgs/spack_repo/ukri_bench/
  repo.yaml                        # namespace and Package API version
  packages/
    bench_dolfinx/package.py       # DOLFINx benchmark (CMake; CPU/CUDA/ROCm)
    benchmark_flamegpu/package.py  # FLAMEGPU benchmark (CMake; CUDA/ROCm)
    fenics_dolfinx/package.py      # builtin fenics-dolfinx + nvcc patch for 0.11
    mesa/package.py                # builtin mesa + glibc 2.43 (C23) patch for 24.3-25.0
    nemo/package.py                # NEMO ocean model (makenemo/FCM)
    nemo/nemo-wrapper.sh           # run-dir wrapper (placeholders set at install)
.github/
  spack/ci-env.yaml                # Spack environment template for build workflows
  spack/packages.yaml              # CI package requirements (target, CUDA/ROCm pins)
  spack/concretizer.yaml           # CI concretizer settings (shared with ci.yml)
  spack/versions.env               # Spack release and spack-packages commit (all workflows)
  workflows/ci.yml                 # ruff + spack audit/spec
  workflows/build-package.yml      # reusable: build one package
  workflows/build-<pkg>.yml        # per-package callers
```

Package directories use underscores (`bench_dolfinx`); package names use
hyphens (`bench-dolfinx`).

## Package conventions

- Header: copyright line and `# SPDX-License-Identifier: MIT` (the repository
  is MIT licensed).
- Imports: build-system classes from `spack_repo.builtin.build_systems.*`,
  then a blank line, then `from spack.package import *`. `Package` and
  `GenericBuilder` come from `spack.package` (Package API v2.2+), not
  `build_systems.generic`.
- Class body order: docstring, `homepage`/`git`, `maintainers`, `license`,
  `version`, variants, conflicts, `depends_on`, then methods.
- Every package declares `maintainers(...)` and `license(...)` (SPDX
  identifier of the upstream code, not of this repository). Overrides of
  builtin packages (e.g. `fenics_dolfinx`, `mesa`) inherit both; do not redeclare.
- Prefer `spec.satisfies(...)` over `"+x" in spec`, and `%fortran=gcc`-style
  checks when the language matters.
- Libraries a package links against must be link dependencies (the default
  type), not `type="build"`. Spack's compiler wrapper then adds RPATHs; do not
  hand-write `-Wl,-rpath` flags.
- Use `spec[...].libs` / `.ld_flags` rather than hard-coded `-L`/`-l` paths.
- Express unsupported combinations as `conflicts()`/`requires()` so they fail
  at concretization, not mid-build.
- Version ranges like `@3.2:` also match infinite versions (`main`, `master`,
  `develop`). Check what the concretizer actually picks.
- Before adding a dependency constraint, check that the builtin repo
  (spack/spack-packages) has a matching version and variant. Language
  virtuals such as `cuda-lang`/`hip-lang` have no builtin providers yet.

## Checks

Run locally before pushing:

```console
ruff check .
ruff format --check .
```

`ruff.toml` sets line length 99 and allows Spack's star import.

With Spack available:

```console
spack repo add spack_pkgs/spack_repo/ukri_bench
spack audit packages bench-dolfinx benchmark-flamegpu nemo
spack spec bench-dolfinx
spack spec benchmark-flamegpu
spack spec nemo +openmp
```

There is no local test suite; CI is the integration test.

## CI

- `ci.yml`: ruff, then `spack audit` and `spack spec` for several variants,
  plus a few specs that must be rejected, against the pinned spack-packages
  commit.
- `build-bench-dolfinx.yml`, `build-nemo.yml`: call `build-package.yml`, which
  builds the package on each OS image in its matrix, checks the installed
  `executable`, and runs the caller's smoke test. bench-dolfinx's GPU builds
  run after its CPU build (which caches their shared dependencies) and are
  compile-only. Dependencies are taken from
  and pushed to the Spack OCI build cache
  `ghcr.io/ukri-bench/spack-packages-buildcache`; the package itself is always
  built from source. Dependencies built from source are pushed as soon as each
  is installed (Spack autopush), and the cache index is updated even when the
  job fails or is cancelled, so partial progress is kept. Fork PRs only read.
- Version pins: the Spack release (`SPACK_VERSION`) and spack-packages commit
  (`SPACK_PACKAGES_COMMIT`) are set once, in `.github/spack/versions.env`.
  `ci.yml` and `build-package.yml` load that file into the job environment
  and pass the values to `spack/setup-spack`. Bump them deliberately: a new
  spack-packages commit re-solves the graph and can invalidate cached binaries.
  CUDA and ROCm versions are pinned in `.github/spack/packages.yaml` (shared
  by `ci.yml` and the build workflows); bump them with the commit.
- Do not point the build cache at `ghcr.io/ukri-bench/spack-buildcache`. It
  belongs to `benchmark-dolfinx`, and this repository cannot write to it.
- A cold cache means a long first build (dependencies from source).

## Working in this repo

- Keep changes to a package's user-facing interface (variant names, defaults,
  install layout) explicit in the PR description; downstream benchmark repos
  depend on them.
- When adding a package, add a `build-<pkg>.yml` caller (copy an existing one;
  update `paths`, `package`, `executable` and the smoke test) and list it in
  `README.md`.
