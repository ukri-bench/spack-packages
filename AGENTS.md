# AGENTS.md

Guidance for coding agents (and humans) working in this repository.

## What this is

A [Spack](https://spack.io) package repository, namespace `ukri_bench`, for
the UKRI Living Benchmarks. It targets Spack v1.x and Package API v2.0
(`spack_pkgs/spack_repo/ukri_bench/repo.yaml`).

```
spack-repo-index.yaml              # lets `spack repo add <git url>` find the repo
spack_pkgs/spack_repo/ukri_bench/
  repo.yaml                        # namespace and Package API version
  packages/
    bench_dolfinx/package.py       # DOLFINx benchmark (CMake; CPU/CUDA/ROCm)
    nemo/package.py                # NEMO ocean model (makenemo/FCM)
    nemo/nemo-wrapper.sh           # run-dir wrapper; @PREFIX@/@MPI@/@XIOS@ filled at install
.github/
  spack/ci-env.yaml                # Spack environment template for build workflows
  spack/versions.env               # Spack release and spack-packages commit (all workflows)
  actions/setup-spack/action.yml   # Spack with those pins + this repo; used by benchmark repos
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
  then a blank line, then `from spack.package import *`.
- Class body order: docstring, `homepage`/`git`, `maintainers`, `version`,
  variants, conflicts, `depends_on`, then methods.
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
spack audit packages bench-dolfinx nemo
spack spec bench-dolfinx
spack spec nemo +openmp
```

There is no local test suite; CI is the integration test.

## CI

- `ci.yml`: ruff, then `spack audit` and `spack spec` for several variants,
  against the pinned spack-packages commit.
- `build-bench-dolfinx.yml`, `build-nemo.yml`: build the package in an
  `ubuntu:26.04` container and run a smoke test. Dependencies are taken from
  and pushed to the Spack OCI build cache
  `ghcr.io/ukri-bench/spack-packages-buildcache`; the package itself is always
  built from source. Dependencies built from source are pushed as soon as each
  is installed (Spack autopush), and the cache index is updated even when the
  job fails or is cancelled, so partial progress is kept. Fork PRs only read.
- Version pins: the Spack release (`SPACK_VERSION`) and spack-packages commit
  (`SPACK_PACKAGES_COMMIT`) are set once, in `.github/spack/versions.env`.
  Workflows install Spack with `.github/actions/setup-spack`, which reads that
  file; benchmark repositories use the same action
  (`ukri-bench/spack-packages/.github/actions/setup-spack@main`), so they share
  the pins and the build cache. Bump them deliberately: a new spack-packages
  commit re-solves the graph and can invalidate cached binaries.
- Do not point the build cache at `ghcr.io/ukri-bench/spack-buildcache`. It
  belongs to `benchmark-dolfinx`, and this repository cannot write to it.
- A cold cache means a long first build (dependencies from source).

## Working in this repo

- Keep changes to a package's user-facing interface (variant names, defaults,
  install layout) explicit in the PR description; downstream benchmark repos
  depend on them.
- When adding a package, add a `build-<pkg>.yml` caller (copy an existing one;
  update `paths`, `package` and the smoke test) and list it in `README.md`.
