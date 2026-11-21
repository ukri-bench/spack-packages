#!/usr/bin/env python3

# Copyright 2025 Aditya Sadawarte
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)


import argparse
import os
import textwrap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mpi", action="store_true", help="Enable MPI support")
    parser.add_argument("--xios", action="store_true", help="Enable XIOS support")
    parser.add_argument("--prefix", type=str, required=True, help="Prefix path")
    args = parser.parse_args()

    wrapper_script = f"""\
    #!/bin/bash

    show_help() {{
    cat << EOF
      Usage: $(basename "$0") [OPTIONS]

      Options:
      -d, --dir path        Run directory path (default: $PWD/NEMO_RUNDIR)
    EOF
      {'''echo "  -i, --lon num         (required) No. of NEMO MPI processes in the i (longitudinal) direction"
      echo "  -j, --lat num         (required) No. of NEMO MPI processes in the j (latitudinal) direction"''' if args.mpi else ''}
      {'echo "  -x, --xproc num       No. of XIOS servers (set to 0 if using attached mode) (default: 0)"' if args.xios else ''}
    cat << EOF
      -t, --timesteps num   No. of timesteps (default: 24)
      -n, --namelist path   Namelist file path (default: nemo_path/EXP00/namelist_cfg)
      --extra-paths paths   Extra paths to link in the run directory (colon separated)
      +stats                Enable run.stat
      +timings              Enable NEMO timings in the timing.output file (requires: gnuplot)
      +icebergs             Enable icebergs
      -h, --help            Show this help message and exit
    EOF
    }}

    REF_DIR="{args.prefix}/EXP00"
    RUN_DIR="${{PWD}}/NEMO_RUNDIR"
    XPROC=0
    RUNLEN=24
    NML="${{REF_DIR}}/namelist_cfg"
    TIMINGS=0
    STATS=0
    ICEBERGS=0
    {'' if args.mpi else '''
    IPROC=1
    JPROC=1
    '''}

    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        -d|--dir)
          RUN_DIR="$2"
          shift 2
          ;;
        {'''-i|--lon)
            IPROC="$2"
            shift 2
          ;;
        -j|--lat)
            JPROC="$2"
            shift 2
          ;;''' if args.mpi else ''}
        {'''-x|--xproc)
            XPROC="$2"
            shift 2
          ;;''' if args.xios else ''}
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
          echo "Unknown option: $1"
          show_help
          exit 1
          ;;
        *)
          echo "Unexpected argument: $1"
          show_help
          exit 1
          ;;
      esac
    done

    {'''if [[ -z "$IPROC" ]]; then
      echo "Error: -i is required."
      show_help
      exit 1
    fi

    if [[ -z "$JPROC" ]]; then
      echo "Error: -j is required."
      show_help
      exit 1
    fi''' if args.mpi else ''}

    if [[ ! -f "${{NML}}" ]]; then
      echo "No such namelist file ${{NML}}"
      exit 1
    fi

    echo "RUN DIR is ${{RUN_DIR}}"

    # Only remove an existing run directory if it was created by this wrapper
    MARKER=".nemo-wrapper-rundir"
    if [[ -e "${{RUN_DIR}}" ]]; then
      if [[ -f "${{RUN_DIR}}/${{MARKER}}" ]]; then
        rm -r "${{RUN_DIR}}"
      else
        echo "Error: ${{RUN_DIR}} exists and was not created by $(basename "$0"); not removing it."
        exit 1
      fi
    fi
    cp -ansT "${{REF_DIR}}" "${{RUN_DIR}}"
    touch "${{RUN_DIR}}/${{MARKER}}"
    cp --remove-destination "${{NML}}" "${{RUN_DIR}}/namelist_cfg"
    {'cp --remove-destination "${REF_DIR}/iodef.xml" "${RUN_DIR}/iodef.xml"' if args.xios else ''}

    IFS=':' read -ra extra_paths <<< "${{EXTRA_PATHS}}"
    for p in "${{extra_paths[@]}}"; do
      find "$(realpath "${{p}}")" -type f -exec ln -s {{}} "${{RUN_DIR}}" \\;
    done

    CFG="${{RUN_DIR}}/namelist_cfg"
    f90nml -g nammpp -v jpni=${{IPROC}} "${{CFG}}" "${{CFG}}"
    f90nml -g nammpp -v jpnj=${{JPROC}} "${{CFG}}" "${{CFG}}"
    f90nml -g namrun -v nn_itend=${{RUNLEN}} "${{CFG}}" "${{CFG}}"

    if [[ ${{TIMINGS}} -eq 1 ]]; then
      f90nml -g namctl -v ln_timing=true "${{CFG}}" "${{CFG}}"
    else
      f90nml -g namctl -v ln_timing=false "${{CFG}}" "${{CFG}}"
    fi

    if [[ ${{STATS}} -eq 1 ]]; then
      f90nml -g namctl -v sn_cfctl%l_runstat=true "${{CFG}}" "${{CFG}}"
    else
      f90nml -g namctl -v sn_cfctl%l_runstat=false "${{CFG}}" "${{CFG}}"
    fi

    if [[ ${{ICEBERGS}} -eq 1 ]]; then
      f90nml -g namberg -v ln_icebergs=true "${{CFG}}" "${{CFG}}"
    else
      f90nml -g namberg -v ln_icebergs=false "${{CFG}}" "${{CFG}}"
    fi
    """

    wrapper_path = os.path.join(args.prefix, "bin")
    os.makedirs(wrapper_path, exist_ok=True)
    with open(os.path.join(wrapper_path, "nemo-wrapper"), "w") as f:
        f.write(textwrap.dedent(wrapper_script))
    os.chmod(os.path.join(wrapper_path, "nemo-wrapper"), 0o755)


if __name__ == "__main__":
    main()
