#!/usr/bin/env python3

# Copyright 2025 Aditya Sadawarte
#
# SPDX-License-Identifier: MIT

"""Generate the nemo-wrapper script, which prepares a NEMO run directory."""

import argparse
import os
import textwrap

MPI_HELP = """\
  echo "  -i, --lon num         (required) No. of MPI processes in the i (longitudinal) direction"
  echo "  -j, --lat num         (required) No. of MPI processes in the j (latitudinal) direction"\
"""

MPI_OPTIONS = """\
    -i|--lon)
      IPROC="$2"
      shift 2
      ;;
    -j|--lat)
      JPROC="$2"
      shift 2
      ;;\
"""

MPI_CHECKS = """\
if [[ -z "${IPROC}" ]]; then
  echo "Error: -i is required." >&2
  show_help >&2
  exit 1
fi

if [[ -z "${JPROC}" ]]; then
  echo "Error: -j is required." >&2
  show_help >&2
  exit 1
fi\
"""

XIOS_COPY = 'cp --remove-destination "${REF_DIR}/iodef.xml" "${RUN_DIR}/iodef.xml"'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mpi", action="store_true", help="Enable MPI support")
    parser.add_argument("--xios", action="store_true", help="Enable XIOS support")
    parser.add_argument("--prefix", type=str, required=True, help="Prefix path")
    args = parser.parse_args()

    # Placeholders are substituted after dedent so that inserted blocks keep their layout
    template = textwrap.dedent(
        """\
        #!/bin/bash
        # Prepare a NEMO run directory from the installed reference experiment (EXP00).
        set -euo pipefail

        show_help() {
        cat << EOF
          Usage: $(basename "$0") [OPTIONS]

          Prepare a NEMO run directory. NEMO itself is not run.

          Options:
          -d, --dir path        Run directory path (default: $PWD/NEMO_RUNDIR)
        EOF
        @MPI_HELP@
        cat << EOF
          -t, --timesteps num   No. of timesteps (default: 24)
          -n, --namelist path   Namelist file path (default: nemo_path/EXP00/namelist_cfg)
          --extra-paths paths   Extra paths to link in the run directory (colon separated)
          +stats                Enable run.stat
          +timings              Enable NEMO timings in the timing.output file
          +icebergs             Enable icebergs
          -h, --help            Show this help message and exit
        EOF
        }

        REF_DIR="@PREFIX@/EXP00"
        RUN_DIR="${PWD}/NEMO_RUNDIR"
        RUNLEN=24
        NML="${REF_DIR}/namelist_cfg"
        EXTRA_PATHS=""
        TIMINGS=0
        STATS=0
        ICEBERGS=0
        IPROC=@IPROC@
        JPROC=@JPROC@

        while [[ "$#" -gt 0 ]]; do
          case "$1" in
            -d|--dir)
              RUN_DIR="$2"
              shift 2
              ;;
        @MPI_OPTIONS@
            -t|--timesteps)
              RUNLEN="$2"
              shift 2
              ;;
            -n|--namelist)
              NML="$2"
              shift 2
              ;;
            --extra-paths)
              EXTRA_PATHS="$2"
              shift 2
              ;;
            +stats)
              STATS=1
              shift
              ;;
            +timings)
              TIMINGS=1
              shift
              ;;
            +icebergs)
              ICEBERGS=1
              shift
              ;;
            -h|--help)
              show_help
              exit 0
              ;;
            -*)
              echo "Unknown option: $1" >&2
              show_help >&2
              exit 1
              ;;
            *)
              echo "Unexpected argument: $1" >&2
              show_help >&2
              exit 1
              ;;
          esac
        done

        @MPI_CHECKS@

        if [[ ! -f "${NML}" ]]; then
          echo "No such namelist file ${NML}" >&2
          exit 1
        fi

        echo "RUN DIR is ${RUN_DIR}"

        # Only remove an existing run directory if it was created by this wrapper
        MARKER=".nemo-wrapper-rundir"
        if [[ -e "${RUN_DIR}" ]]; then
          if [[ -f "${RUN_DIR}/${MARKER}" ]]; then
            rm -r "${RUN_DIR}"
          else
            echo "Error: ${RUN_DIR} exists and was not created by $(basename "$0")." >&2
            exit 1
          fi
        fi
        cp -ansT "${REF_DIR}" "${RUN_DIR}"
        touch "${RUN_DIR}/${MARKER}"
        cp --remove-destination "${NML}" "${RUN_DIR}/namelist_cfg"
        @XIOS_COPY@

        if [[ -n "${EXTRA_PATHS}" ]]; then
          IFS=':' read -ra extra_paths <<< "${EXTRA_PATHS}"
          for p in "${extra_paths[@]}"; do
            find "$(realpath "${p}")" -type f -exec ln -s {} "${RUN_DIR}" \\;
          done
        fi

        to_bool() { [[ "$1" -eq 1 ]] && echo true || echo false; }

        CFG="${RUN_DIR}/namelist_cfg"
        f90nml -g nammpp -v jpni="${IPROC}" "${CFG}" "${CFG}"
        f90nml -g nammpp -v jpnj="${JPROC}" "${CFG}" "${CFG}"
        f90nml -g namrun -v nn_itend="${RUNLEN}" "${CFG}" "${CFG}"
        f90nml -g namctl -v ln_timing="$(to_bool "${TIMINGS}")" "${CFG}" "${CFG}"
        f90nml -g namctl -v sn_cfctl%l_runstat="$(to_bool "${STATS}")" "${CFG}" "${CFG}"
        f90nml -g namberg -v ln_icebergs="$(to_bool "${ICEBERGS}")" "${CFG}" "${CFG}"
        """
    )

    substitutions = {
        "@PREFIX@": args.prefix,
        "@MPI_HELP@": MPI_HELP if args.mpi else "",
        "@MPI_OPTIONS@": MPI_OPTIONS if args.mpi else "",
        "@MPI_CHECKS@": MPI_CHECKS if args.mpi else "",
        "@IPROC@": '""' if args.mpi else "1",
        "@JPROC@": '""' if args.mpi else "1",
        "@XIOS_COPY@": XIOS_COPY if args.xios else "",
    }
    script = template
    for key, value in substitutions.items():
        script = script.replace(key, value)

    wrapper_dir = os.path.join(args.prefix, "bin")
    os.makedirs(wrapper_dir, exist_ok=True)
    wrapper = os.path.join(wrapper_dir, "nemo-wrapper")
    with open(wrapper, "w") as f:
        f.write(script)
    os.chmod(wrapper, 0o755)


if __name__ == "__main__":
    main()
