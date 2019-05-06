from mpi4py import MPI
import math
import numpy as np
from string import Template
import os
import time

# =============================================================================
# Experiment set up
# =============================================================================

# Read in SOW parameters
LHsamples = np.loadtxt('./LHsamples.txt') 
nSamples = len(LHsamples[:,0])

# Read/define relevant structures for each uncertainty
reservoirs = np.genfromtxt('reservoirs.txt',dtype='str').tolist()
transbasin = np.genfromtxt('TBD.txt',dtype='str').tolist()
irrigation = np.genfromtxt('irrigation.txt',dtype='str').tolist()
mun_ind = np.genfromtxt('M_I.txt',dtype='str').tolist()
env_flows = ['7202003']
shoshone = ['5300584']

# List IDs of structures of interest for output files
IDs = np.genfromtxt('metrics_structures.txt',dtype='str').tolist() 
info_clmn = [2, 4, 17] # Define columns of aspect of interest 

# =============================================================================
# Load global information (applicable to all SOW)
# =============================================================================
# For RSP
T = open('./Experiment_files/cm2015B_template.rsp', 'r')
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

# For RES
# get unsplit data to rewrite everything that's unchanged
with open('./Experiment_files/cm2015B.res','r') as f:
    all_data_RES = [x for x in f.readlines()]       
f.close() 

# For DDR
# get unsplit data to rewrite everything that's unchanged
with open('./Experiment_files/cm2015B.ddr','r') as f:
    all_data_DDR = [x for x in f.readlines()]       
f.close() 
column_lengths=[12,24,12,16,8,8]
split_line = ['']*len(column_lengths)
character_breaks=np.zeros(len(column_lengths),dtype=int)
character_breaks[0]=column_lengths[0]
for i in range(1,len(column_lengths)):
    character_breaks[i]=character_breaks[i-1]+column_lengths[i]

# For EVA
# split data on periods
with open('./Experiment_files/cm2015.eva','r') as f:
    all_split_data_EVA = [x.split() for x in f.readlines()]    
f.close() 
# get unsplit data to rewrite firstLine # of rows
with open('./Experiment_files/cm2015.eva','r') as f:
    all_data_EVA = [x for x in f.readlines()]
f.close()

# =============================================================================
# Define functions that generate each type of input file 
# =============================================================================

# Function for DDM files
def writenewDDM(structures, firstLine, sampleCol, k, l):    
    allstructures = []
    for m in range(len(structures)):
        allstructures.extend(structures[m])
    with open('./Experiment_files/cm2015B_S'+ str(k+1) + '_' + str(l+1) + '.iwr') as f:
        sample_IWR = [x.split() for x in f.readlines()[463:]]       
    f.close() 
    new_data = []
    irrigation_encounters = np.zeros(len(structures[0]))
    # Divide Shoshone demand multiplier into on and off 
    if LHsamples[k,4]>0.5: 
        multiplier = 1
    else:
        multiplier = 0
    for i in range(len(all_split_data_DDM)-firstLine):
        row_data = []
        # To store the change between historical and sample irrigation demand (12 months + Total)
        change = np.zeros(13) 
        # Split first 3 columns of row on space
        # This is because the first month is lumped together with the year and the ID when spliting on periods
        row_data.extend(all_split_data_DDM[i+firstLine][0].split())
        # If the structure is not in the ones we care about then do nothing
        if row_data[1]==shoshone[0]: #If the structure is the Shoshone
            # apply multiplier to 1st month
            row_data[2] = str(int(float(row_data[2])*multiplier))
            # apply multipliers to rest of the columns
            for j in range(len(all_split_data_DDM[i+firstLine])-2):
                row_data.append(str(int(float(all_split_data_DDM[i+firstLine][j+1])*multiplier)))
        elif row_data[1] in structures[0]:                
            line_in_iwr = int(irrigation_encounters[structures[0].index(row_data[1])]*len(structures[0]) + structures[0].index(row_data[1]))
            irrigation_encounters[structures[0].index(row_data[1])]=+1
            for m in range(len(change)):
                change[m]= float(sample_IWR[line_in_iwr][2+m])-float(hist_IWR[line_in_iwr][2+m])
            # apply change to 1st month
            row_data[2] = str(int(float(row_data[2])+change[0]))
            # apply multipliers to rest of the columns
            for j in range(len(all_split_data_DDM[i+firstLine])-2):
                row_data.append(str(int(float(all_split_data_DDM[i+firstLine][j+1])+change[j+1])))                  
        elif row_data[1] not in allstructures:
            for j in range(len(all_split_data_DDM[i+firstLine])-2):
                row_data.append(str(int(float(all_split_data_DDM[i+firstLine][j+1]))))
        else:
            for m in range(1,len(structures)-1):
                if row_data[1] in structures[m]:
                    # apply multiplier to 1st month
                    row_data[2] = str(int(float(row_data[2])*LHsamples[k,sampleCol[m]]))
                    # apply multipliers to rest of the columns
                    for j in range(len(all_split_data_DDM[i+firstLine])-2):
                        row_data.append(str(int(float(all_split_data_DDM[i+firstLine][j+1])*LHsamples[k,sampleCol[m]])))                        
        # append row of adjusted data
        new_data.append(row_data)                
    # write new data to file
    f = open('./Experiment_files/'+ 'cm2015B.ddm'[0:-4] + '_S' + str(k+1) + '_' + str(l+1) + 'cm2015B.ddm'[-4::],'w')
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

# Function for RES files
def writenewRES(lines, sampleCol, k):
    copy_all_data_RES = np.copy(all_data_RES)       
    # Change only the specific lines
    for j in range(len(lines)):
        split_line = all_data_RES[lines[j]].split('.')
        split_line[1] = ' ' + str(int(float(split_line[1])*LHsamples[k,sampleCol]))
        copy_all_data_RES[lines[j]]=".".join(split_line)                
    # write new data to file
    f = open('./Experiment_files/'+ 'cm2015B.res'[0:-4] + '_S' + str(k+1) + 'cm2015B.res'[-4::],'w')
    for i in range(len(copy_all_data_RES)):
        f.write(copy_all_data_RES[i])
    f.close()
    
    return None

# Function for DDR files
def writenewDDR(lines, sampleCol, k):
    copy_all_data = np.copy(all_data_DDR)
    # Change only for specific samples
    if LHsamples[k,5]>0.5:
        # Change only the specific lines
        for j in range(len(lines)):
            split_line[0]=all_data_DDR[lines[j]][0:character_breaks[0]]
            for i in range(1,len(split_line)):
                split_line[i]=all_data_DDR[lines[j]][character_breaks[i-1]:character_breaks[i]]
            split_line[3] = (column_lengths[3]-len(str(1.00000)))*' '+str(1.00000)
            split_line[4] = (column_lengths[4]-len(str(405.83)))*' '+str(405.83)
            copy_all_data[lines[j]]="".join(split_line)+'\n'                
    # write new data to file
    f = open('./Experiment_files/'+ 'cm2015B.ddr'[0:-4] + '_S' + str(k+1) + 'cm2015B.ddr'[-4::],'w')
    for i in range(len(copy_all_data)):
        f.write(copy_all_data[i])
    f.close()
    
    return None    

# Function for EVA files
def writenewEVA(k):
    new_data = []
    for i in range(len(all_split_data_EVA)-35):
        row_data = []
        row_data.append(all_split_data_EVA[i+35][0])
        # apply multipliers to all but 1st column
        for j in range(len(all_split_data_EVA[i+35])-1):
            row_data.append(float(all_split_data_EVA[i+35][j+1])+LHsamples[k,6])            
        # append row of adjusted data
        new_data.append(row_data)            
    # write new data to file
    f = open('./Experiment_files/cm2015_S' + str(k+1) + '.eva','w')
    # write firstLine # of rows as in initial file
    for i in range(35):
        f.write(all_data_EVA[i])        
    for i in range(len(new_data)):
        # write ID and first month of adjusted data
        if new_data[i][0] != '10004':
            f.write(5*' ' + new_data[i][0] + (15-len(str("{0:.2f}".format(new_data[i][1]))))*' ' + str("{0:.2f}".format(new_data[i][1])))
        else:
            f.write(5*' ' + new_data[i][0] + (15-len(str("{0:.4f}".format(new_data[i][1]))))*' ' + str("{0:.4f}".format(new_data[i][1])))            
        # write remaining months of adjusted data
        for j in range(len(new_data[i])-2):
            if new_data[i][0] != '10004':
                f.write((8-len(str("{0:.2f}".format(new_data[i][j+2]))))*' ' + str("{0:.2f}".format(new_data[i][j+2])))
            else:
                f.write((8-len(str("{0:.4f}".format(new_data[i][j+2]))))*' ' + str("{0:.4f}".format(new_data[i][j+2])))                
        f.write('\n')        
    f.close()

# =============================================================================
# Define output extraction function
# =============================================================================
  
def getinfo(k, j):
    line_out = '' #Empty line for storing data to print in file   
    # Get summarizing files for each structure and aspect of interest from the .xdd or .xss files
    for ID in IDs:
        if not os.path.exists('./Infofiles/' + ID):
            os.makedirs('./Infofiles/' + ID)
        with open ('./Infofiles/' +  ID + '/' + ID + '_info_' + str(k+1) + '_' + str(j+1) + '.txt','w') as f:
            try:
                with open ('./Experiment_files/cm2015B_S' + str(k+1) + '_' + str(j+1) + '.xdd', 'rt') as xdd_file:
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
for k in range(start, stop):
    for j in range(1): 
        d = {}
        d['IWR'] = 'cm2015B_S' + str(k+1) + '_' + str(j+1) + '.iwr'
        d['XBM'] = 'cm2015x_S' + str(k+1) + '_' + str(j+1) + '.xbm'
        d['DDR'] = 'cm2015B_S' + str(k+1) + '.ddr'
        d['DDM'] = 'cm2015B_S' + str(k+1) + '_' + str(j+1) + '.ddm'
        d['EVA'] = 'cm2015_S' + str(k+1) + '.eva'
        d['RES'] = 'cm2015B_S' + str(k+1) + '.res'
        S1 = template_RSP.safe_substitute(d)
        f1 = open('./Experiment_files/cm2015B_S' + str(k+1) + '_' + str(j+1) + '.rsp', 'w')
        f1.write(S1)    
        f1.close()
        writenewDDM([irrigation, transbasin, mun_ind, shoshone], 779, [0, 2, 3, 4], k, j)
        writenewRES([395,348,422,290,580,621], 1, k)
        writenewDDR([2019,2020,2021], 5, k)
        writenewEVA(k)
        os.system("./Experiment_files/statemod Experiment_files/cm2015B_S{}_{} -simulate".format(k+1,j+1))
        # Wait 2 minutes for the experiment to run before getting outputs
        time.sleep(120)
        # Check if output file exists and if it's of the right size before extracting outputs
        while not (os.path.exists('./Experiment_files/cm2015B_S'+str(k+1)+ '_' + str(j+1) + '.xdd') and \
                  os.path.getsize('./Experiment_files/cm2015B_S'+str(k+1)+ '_' + str(j+1) + '.xdd') >> 10 > 502000):
            time.sleep(1)
        getinfo(k,j)
        os.system("rm ./Experiment_files/cm2015B_S{}_{}.xdd".format(k+1,j+1))
        print('Finished with '+str(k+1)+ '_' + str(j+1))