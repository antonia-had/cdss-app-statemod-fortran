import numpy as np
import pandas as pd
import sys
from mpi4py import MPI
sys.path.append('../')
from SALib.analyze import delta
import statsmodels.api as sm
import scipy.stats
import math


design = str(sys.argv[1])
LHsamples = np.loadtxt('../Qgen/' + design + '.txt') 
param_bounds=np.loadtxt('../Qgen/uncertain_params_'+design[10:-5]+'.txt', usecols=(1,2))
realizations = 10
percentiles = np.arange(0,100)
param_names=[x.split(' ')[0] for x in open('../Qgen/uncertain_params_'+design[10:-5]+'.txt').readlines()]
params_no = len(LHsamples[0,:])
problem = {
    'num_vars': params_no,
    'names': param_names,
    'bounds': param_bounds.tolist()
}
all_IDs = np.genfromtxt('../Structures_files/metrics_structures.txt',dtype='str').tolist() 
nStructures = len(all_IDs)

# deal with fact that calling result.summary() in statsmodels.api
# calls scipy.stats.chisqprob, which no longer exists
scipy.stats.chisqprob = lambda chisq, df: scipy.stats.chi2.sf(chisq, df)

def fitOLS(dta, predictors):
    # concatenate intercept column of 1s
    dta['Intercept'] = np.ones(np.shape(dta)[0])
    # get columns of predictors
    cols = dta.columns.tolist()[-1:] + predictors
    #fit OLS regression
    ols = sm.OLS(dta['Shortage'], dta[cols])
    result = ols.fit()
    return result

def sensitivity_analysis_per_structure(ID):
    '''
    Perform analysis for max shortage duration at each magnitude
    '''
    durations = np.load('../'+design+'/MultiyearShortageCurves/' + ID + '.npy')
    dta = pd.DataFrame(data = np.repeat(LHsamples, realizations, axis = 0), columns=param_names)
    DELTA = pd.DataFrame(np.zeros((params_no, len(percentiles))), columns = percentiles)
    DELTA_conf = pd.DataFrame(np.zeros((params_no, len(percentiles))), columns = percentiles)
    S1 = pd.DataFrame(np.zeros((params_no, len(percentiles))), columns = percentiles)
    S1_conf = pd.DataFrame(np.zeros((params_no, len(percentiles))), columns = percentiles)
    R2_scores = pd.DataFrame(np.zeros((params_no, len(percentiles))), columns = percentiles)
    DELTA.index=DELTA_conf.index=S1.index=S1_conf.index = R2_scores.index = param_names
    for i in range(len(percentiles)):
        if durations[i].any():
            # Delta Method analysis
            try:
                result= delta.analyze(problem, np.repeat(LHsamples, realizations, axis = 0), durations[i], print_to_console=False)
                DELTA[percentiles[i]]= result['delta']
                DELTA_conf[percentiles[i]] = result['delta_conf']
                S1[percentiles[i]]=result['S1']
                S1_conf[percentiles[i]]=result['S1_conf']
            except:
                pass
            # OLS regression analysis
            dta['Shortage']=durations[i]
            R2_scores = pd.DataFrame(np.zeros(params_no))
            R2_scores.index = param_names
            for m in range(params_no):
                predictors = dta.columns.tolist()[m:(m+1)]
                result = fitOLS(dta, predictors)
                R2_scores.at[param_names[m],0]=result.rsquared
    R2_scores.to_csv('../'+design+'/Max_Duration_Sensitivity_analysis/'+ ID + '_R2.csv')
    S1.to_csv('../'+design+'/Max_Duration_Sensitivity_analysis/'+ ID + '_S1.csv')
    S1_conf.to_csv('../'+design+'/Max_Duration_Sensitivity_analysis/'+ ID + '_S1_conf.csv')
    DELTA.to_csv('../'+design+'/Max_Duration_Sensitivity_analysis/'+ ID + '_DELTA.csv')
    DELTA_conf.to_csv('../'+design+'/Max_Duration_Sensitivity_analysis/'+ ID + '_DELTA_conf.csv')
        
# =============================================================================
# Start parallelization (running each structure in parallel)
# =============================================================================
    
# Begin parallel simulation
comm = MPI.COMM_WORLD

# Get the number of processors and the rank of processors
rank = comm.rank
nprocs = comm.size

# Determine the chunk which each processor will neeed to do
count = int(math.floor(nStructures/nprocs))
remainder = nStructures % nprocs

# Use the processor rank to determine the chunk of work each processor will do
if rank < remainder:
	start = rank*(count+1)
	stop = start + count + 1
else:
	start = remainder*(count+1) + (rank-remainder)*count
	stop = start + count

# Run simulation
for k in range(start, stop):
    sensitivity_analysis_per_structure(all_IDs[k])