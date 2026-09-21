"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np

MASS=dict(zip("ARNDCEQGHLKMFPSTWYV",[71.037114,156.101111,114.042927,115.026943,103.009185,129.042593,128.058578,57.021464,137.058912,113.084064,128.094963,131.040485,147.068414,97.052764,87.032028,101.047679,186.079313,163.063329,99.068414]))

def decode_spectrum(peaks, precursor_mass, charge):
    target=precursor_mass-18.010565
    masses=np.asarray(peaks)[:,0]; intensities=np.asarray(peaks)[:,1]
    tolerance=precursor_mass*50e-6
    beam=[(0.,"",0.)]; best=None
    for length in range(1,25):
        extensions=[]
        for mass,sequence,score in beam:
            for aa,weight in MASS.items():
                newmass=mass+weight
                if newmass > target+tolerance: continue
                bmatch=np.abs(masses-(newmass+1.007276))<.03
                ymatch=np.abs(masses-(precursor_mass-newmass+1.007276))<.03
                newscore=score+float(intensities[bmatch|ymatch].sum())
                newseq=sequence+aa
                if abs(newmass-target)<=tolerance:
                    if best is None or newscore>best[2]:best=(newmass,newseq,newscore)
                else:extensions.append((newmass,newseq,newscore))
        if not extensions:break
        beam=sorted(extensions,key=lambda x:x[2],reverse=True)[:100]
    if best is None:return "",0.
    return best[1],float(best[2]/(1+best[2]))
# EVOLVE-BLOCK-END
