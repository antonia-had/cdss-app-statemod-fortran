from mpi4py import MPI
import math
import numpy as np
from string import Template
import os
import time

# =============================================================================
# Experiment set up
# =============================================================================
nSamples = 10

# Read/define relevant structures for each uncertainty
irrigation = np.genfromtxt('irrigation.txt',dtype='str').tolist()
transbasin = np.genfromtxt('TBD.txt',dtype='str').tolist()

# List IDs of structures of interest for output files
IDs = np.genfromtxt('metrics_structures_short.txt',dtype='str').tolist() 
info_clmn = [2, 4, 17] # Define columns of aspect of interest 

# =============================================================================
# Load global information (applicable to all SOW)
# =============================================================================
# For RSP
T = open('./Experiment_files/cm2015B_template_streamflow.rsp', 'r')
template_RSP = Template(T.read())

# For DDM
# split data on periods (splitting on spaces/tabs doesn't work because some columns are next to each other)
with open('./Experiment_files/cm2015B.ddm','r') as f:
    all_split_data_DDM = [x.split('.') for x in f.readlines()]       
f.close()        
# get unsplit data to rewrite firstLine # of rows
with open('./Experiment_files/cm2015B.ddm','r') as f:
    all_data_DDM = [x for x in f.readlines()]       
f.close() 
# Get historical irrigation rata 
with open('./Experiment_files/cm2015B.iwr','r') as f:
    hist_IWR = [x.split() for x in f.readlines()[463:]]       
f.close() 
# Get uncurtailed demands
with open('./cm2015_export_max.stm','r') as f:
    diversions_uc = [x.split()[1:14] for x in f.readlines()[78:94]]       
f.close() 
uncurtailed = [x[0] for x in diversions_uc] # Get uncurtailed structures

# =============================================================================
# Define functions that generate each type of input file 
# =============================================================================

# Function for DDM files
def writenewDDM(structures, firstLine, sampleCol, l):    
    allstructures = []
    for m in range(len(structures)):
        allstructures.extend(structures[m])
    with open('./Experiment_files/cm2015B_S0_' + str(l+1) + 'f.iwr') as f:
        sample_IWR = [x.split() for x in f.readlines()[463:]]       
    f.close() 
    new_data = []
    irrigation_encounters = np.zeros(len(structures[0]))
    for i in range(len(all_split_data_DDM)-firstLine):
        row_data = []
        # To store the change between historical and sample irrigation demand (12 months + Total)
        change = np.zeros(13) 
        # Split first 3 columns of row on space
        # This is because the first month is lumped together with the year and the ID when spliting on periods
        row_data.extend(all_split_data_DDM[i+firstLine][0].split())
        # If the structure is not in the ones we care about then do nothing
        if row_data[1] in structures[0]: #If the structure is irrigation               
            line_in_iwr = int(irrigation_encounters[structures[0].index(row_data[1])]*len(structures[0]) + structures[0].index(row_data[1]))
            irrigation_encounters[structures[0].index(row_data[1])]=+1
            for m in range(len(change)):
                change[m]= float(sample_IWR[line_in_iwr][2+m])-float(hist_IWR[line_in_iwr][2+m])
            # apply change to 1st month
            row_data[2] = str(int(float(row_data[2])+change[0]))
            # apply change to rest of the columns
            for j in range(len(all_split_data_DDM[i+firstLine])-2):
                row_data.append(str(int(float(all_split_data_DDM[i+firstLine][j+1])+change[j+1])))
        elif row_data[1] in structures[1]: #If the structure is transbasin (to uncurtail)   
            row_data[2] = str(int(float(diversions_uc[uncurtailed.index(row_data[1])][1])))
            for j in range(1,12):
                row_data.append(str(int(float(diversions_uc[uncurtailed.index(row_data[1])][j+1])))) 
        elif row_data[1] not in allstructures:
            for j in range(len(all_split_data_DDM[i+firstLine])-2):
                row_data.append(str(int(float(all_split_data_DDM[i+firstLine][j+1]))))                      
        # append row of adjusted data
        new_data.append(row_data)                
    # write new data to file
    f = open('./Experiment_files/'+ 'cm2015B.ddm'[0:-4] + '_S0_' + str(l+1) + 'cm2015B.ddm'[-4::],'w')
    # write firstLine # of rows as in initial file
    for i in range(firstLine):
        f.write(all_data_DDM[i])            
    for i in range(len(new_data)):
        # write year, ID and first month of adjusted data
        f.write(new_data[i][0] + ' ' + new_data[i][1] + (19-len(new_data[i][1])-len(new_data[i][2]))*' ' + new_data[i][2] + '.')
        # write all but last month of adjusted data
        for j in range(len(new_data[i])-4):
            f.write((7-len(new_data[i][j+3]))*' ' + new_data[i][j+3] + '.')                
        # write last month of adjusted data
        f.write((9-len(new_data[i][-1]))*' ' + new_data[i][-1] + '.' + '\n')            
    f.close()
    
    return None

# =============================================================================
# Define output extraction function
# =============================================================================
  
def getinfo(j):
    line_out = '' #Empty line for storing data to print in file   
    # Get summarizing files for each structure and aspect of interest from the .xdd or .xss files
    for ID in IDs:
        if not os.path.exists('./Infofiles_stationary/' + ID):
            os.makedirs('./Infofiles_stationary/' + ID)
        with open ('./Infofiles_stationary/' +  ID + '/' + ID + '_info_0_' + str(j+1) + '.txt','w') as f:
            try:
                with open ('./Experiment_files/cm2015B_S0_' + str(j+1) + '.xdd', 'rt') as xdd_file:
                    for line in xdd_file:
                        data = line.split()
                        if data:
                            if data[0]==ID:
                                if data[3]!='TOT':
                                    for o in info_clmn:
                                        line_out+=(data[o]+'\t')
                                    f.write(line_out)
                                    f.write('\n')
                                    line_out = ''
                xdd_file.close()
                f.close()
            except IOError:
                f.write('999999\t999999\t999999')
                f.close()

# =============================================================================
# Start parallelization
# =============================================================================
    
# Begin parallel simulation
comm = MPI.COMM_WORLD

# Get the number of processors and the rank of processors
rank = comm.rank
nprocs = comm.size

# Determine the chunk which each processor will neeed to do
count = int(math.floor(nSamples/nprocs))
remainder = nSamples % nprocs

# Use the processor rank to determine the chunk of work each processor will do
if rank < remainder:
	start = rank*(count+1)
	stop = start + count + 1
else:
	start = remainder*(count+1) + (rank-remainder)*count
	stop = start + count

# =============================================================================
# Loop though all SOWs
# =============================================================================
for j in range(start, stop):
    d = {}
    d['IWR'] = 'cm2015B_S0_' + str(j+1) + 'f.iwr'
    d['XBM'] = 'cm2015x_S0_' + str(j+1) + '.xbm'
    d['DDM'] = 'cm2015B_S0_' + str(j+1) + '.ddm'
    S1 = template_RSP.safe_substitute(d)
    f1 = open('./Experiment_files/cm2015B_S0_' + str(j+1) + '.rsp', 'w')
    f1.write(S1)    
    f1.close()
    writenewDDM([irrigation, transbasin], 779, [0, 2], j)
    os.system("./Experiment_files/statemod Experiment_files/cm2015B_S0_{} -simulate".format(j+1))
    # Wait 2 minutes for the experiment to run before getting outputs
    time.sleep(120)
    # Check if output file exists and if it's of the right size before extracting outputs
    while not (os.path.exists('./Experiment_files/cm2015B_S0_' + str(j+1) + '.xdd') and \
              os.path.getsize('./Experiment_files/cm2015B_S0_' + str(j+1) + '.xdd') >> 10 > 502000):
        time.sleep(1)
    getinfo(j)
    os.system("rm ./Experiment_files/cm2015B_S0_{}.xdd".format(j+1))