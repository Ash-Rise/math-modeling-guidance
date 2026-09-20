"""Air / homogeneous epilayer / semi-infinite substrate at oblique incidence.

Time convention exp(-i omega t); wavenumber and damping in cm^-1; d in um.
The reference dielectric functions implement Accepted Decision B01.
"""
import numpy as np

REFERENCES = {'4H': (6.56,798.,970.), '6H': (6.52,797.,969.4)}
NAMES = ['d_um','phonon_gamma_cm-1','plasma_epi_cm-1','drude_epi_cm-1',
         'plasma_sub_cm-1','drude_sub_cm-1','reference_scale',
         'gain_10','gain_15','offset_10','offset_15']

def dielectric(v,p,material,reference='4H'):
    if material=='SiC':
        eps,to,lo=REFERENCES[reference]
        base=eps*p[6]*(1+(lo*lo-to*to)/(to*to-v*v-1j*p[1]*v))
        scale=eps*p[6]
    else:
        lam=1e4/v
        base=p[6]*(11.67316+1/lam**2+0.004482633/(lam**2-1.108205**2))
        scale=11.67316*p[6]
    epi=base-scale*p[2]**2/(v*v+1j*p[3]*v)
    sub=base-scale*p[4]**2/(v*v+1j*p[5]*v)
    return epi,sub

def amplitudes(v,angle,p,material,reference='4H',polarization='unpolarized'):
    e1,e2=dielectric(v,p,material,reference)
    s2=np.sin(np.deg2rad(angle))**2
    q0=np.sqrt(1-s2);q1=np.sqrt(e1-s2);q2=np.sqrt(e2-s2)
    z=np.exp(4j*np.pi*v*p[0]*1e-4*q1)
    result=[]
    for name,y0,y1,y2 in [('s',q0,q1,q2),('p',1/q0,e1/q1,e2/q2)]:
        if polarization not in ['unpolarized',name]:continue
        a=(y0-y1)/(y0+y1);b=(y1-y2)/(y1+y2)
        first=(1-a*a)*b*z
        h=-a*b*z
        result.append((a,first,h))
    return result

def reflectance(v,angle,p,material,beams='multi',reference='4H',polarization='unpolarized'):
    powers=[]
    for a,first,h in amplitudes(v,angle,p,material,reference,polarization):
        r=a+first if beams=='two' else a+first/(1-h)
        powers.append(abs(r)**2)
    return np.mean(powers,axis=0)

def measured(v,angle,p,material,beams='multi',reference='4H',polarization='unpolarized'):
    j=0 if angle==10 else 1
    return p[7+j]*reflectance(v,angle,p,material,beams,reference,polarization)+p[9+j]
