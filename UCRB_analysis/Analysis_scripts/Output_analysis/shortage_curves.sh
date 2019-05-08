#!/bin/bash
#SBATCH --partition=debug
#SBATCH --nodes=1             # specify number of nodes
#SBATCH --ntasks-per-node=1  # specify number of core per node
#SBATCH --export=ALL
#SBATCH -t 0:30:00            # set max wallclock time
#SBATCH --job-name="statemod" # name your job
#SBATCH --output="output.out"

module load python
module load mpi4py
ibrun python shortage_duration_curves_global_experiment.py