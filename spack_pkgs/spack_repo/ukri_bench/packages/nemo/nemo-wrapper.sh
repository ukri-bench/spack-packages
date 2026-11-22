#!/bin/bash
# Copyright 2025 Aditya Sadawarte
#
# SPDX-License-Identifier: MIT
#
# Prepare a NEMO run directory from the installed reference experiment (EXP00).
# @PREFIX@, @MPI@ and @XIOS@ are substituted when the package is installed.
set -euo pipefail

REF_DIR="@PREFIX@/EXP00"
MPI=@MPI@
XIOS=@XIOS@

show_help() {
  cat << EOF
  Usage: $(basename "$0") [OPTIONS]

  Prepare a NEMO run directory. NEMO itself is not run.

  Options:
  -d, --dir path        Run directory path (default: $PWD/NEMO_RUNDIR)
EOF
  if [[ "${MPI}" == true ]]; then
    cat << EOF
  -i, --lon num         (required) No. of MPI processes in the i (longitudinal) direction
  -j, --lat num         (required) No. of MPI processes in the j (latitudinal) direction
EOF
  fi
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

usage_error() {
  echo "$1" >&2
  show_help >&2
  exit 1
}

RUN_DIR="${PWD}/NEMO_RUNDIR"
RUNLEN=24
NML="${REF_DIR}/namelist_cfg"
EXTRA_PATHS=""
TIMINGS=false
STATS=false
ICEBERGS=false
if [[ "${MPI}" == true ]]; then
  IPROC=""
  JPROC=""
else
  IPROC=1
  JPROC=1
fi

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -d|--dir|-i|--lon|-j|--lat|-t|--timesteps|-n|--namelist|--extra-paths)
      [[ "$#" -ge 2 ]] || usage_error "Option $1 requires a value"
      ;;
  esac
  case "$1" in
    -d|--dir)
      RUN_DIR="$2"
      shift 2
      ;;
    -i|--lon|-j|--lat)
      [[ "${MPI}" == true ]] || usage_error "Unknown option: $1"
      if [[ "$1" == -i || "$1" == --lon ]]; then IPROC="$2"; else JPROC="$2"; fi
      shift 2
      ;;
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
      STATS=true
      shift
      ;;
    +timings)
      TIMINGS=true
      shift
      ;;
    +icebergs)
      ICEBERGS=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    -*)
      usage_error "Unknown option: $1"
      ;;
    *)
      usage_error "Unexpected argument: $1"
      ;;
  esac
done

if [[ -z "${IPROC}" || -z "${JPROC}" ]]; then
  usage_error "Error: -i and -j are required."
fi

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
# Mark the directory before populating it, so a failed copy can be retried
mkdir -p "${RUN_DIR}"
touch "${RUN_DIR}/${MARKER}"
cp -ansT "${REF_DIR}" "${RUN_DIR}"
cp --remove-destination "${NML}" "${RUN_DIR}/namelist_cfg"
if [[ "${XIOS}" == true ]]; then
  cp --remove-destination "${REF_DIR}/iodef.xml" "${RUN_DIR}/iodef.xml"
fi

if [[ -n "${EXTRA_PATHS}" ]]; then
  IFS=':' read -ra extra_paths <<< "${EXTRA_PATHS}"
  for p in "${extra_paths[@]}"; do
    [[ -n "${p}" ]] || continue
    find "$(realpath "${p}")" -type f -exec ln -s {} "${RUN_DIR}" \;
  done
fi

CFG="${RUN_DIR}/namelist_cfg"
f90nml -g nammpp -v jpni="${IPROC}" "${CFG}" "${CFG}"
f90nml -g nammpp -v jpnj="${JPROC}" "${CFG}" "${CFG}"
f90nml -g namrun -v nn_itend="${RUNLEN}" "${CFG}" "${CFG}"
f90nml -g namctl -v ln_timing="${TIMINGS}" "${CFG}" "${CFG}"
f90nml -g namctl -v sn_cfctl%l_runstat="${STATS}" "${CFG}" "${CFG}"
f90nml -g namberg -v ln_icebergs="${ICEBERGS}" "${CFG}" "${CFG}"
