"""Independent optics checks and direct recomputation of reported residuals."""
import argparse,json
import numpy as np
from scipy.optimize import minimize_scalar
from inspect_data import ROOT,read_data
from optics import dielectric,reflectance,amplitudes,measured
from solve import data

def transfer(v,angle,p,material):
    # Independent characteristic matrix path; not the Airy denominator.
    e1,e2=dielectric(v,p,material)
    s2=np.sin(np.deg2rad(angle))**2
    qs=[np.full_like(v,np.sqrt(1-s2)),np.sqrt(e1-s2),np.sqrt(e2-s2)]
    beta=2*np.pi*v*p[0]*1e-4*qs[1]
    out=[]
    for ys in [qs,[1/qs[0],e1/qs[1],e2/qs[2]]]:
        c=np.cos(beta);s=np.sin(beta)
        effective=(-1j*ys[1]*s+c*ys[2])/(c-1j*s*ys[2]/ys[1])
        out.append(abs((ys[0]-effective)/(ys[0]+effective))**2)
    return np.mean(out,axis=0)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--folder',default='results/current');args=parser.parse_args()
    folder=ROOT/args.folder;r=json.loads((folder/'results.json').read_text())
    audit={'checks':{},'fits':{},'synthetic':[]}
    max_matrix=0.;max_series=0.
    for material in ['SiC','Si']:
        fit=r['fits'][material+'_multi'];p=fit['vector'];v=np.linspace(450,4000,731)
        for angle in [10,15]:
            max_matrix=max(max_matrix,float(np.max(abs(transfer(v,angle,p,material)-reflectance(v,angle,p,material)))))
            powers=[]
            for a,first,h in amplitudes(v,angle,p,material):
                s=a.copy();term=first.copy()
                for _ in range(80):s+=term;term*=h
                powers.append(abs(s)**2)
            max_series=max(max_series,float(np.max(abs(np.mean(powers,axis=0)-reflectance(v,angle,p,material)))))
        # Known d synthetic data from independent matrix implementation.
        p=np.array(p);p[0]=5.2 if material=='SiC' else 4.2
        y=transfer(v,15,p,material)
        def obj(d):
            trial=p.copy();trial[0]=d
            return np.mean((reflectance(v,15,trial,material)-y)**2)
        opt=minimize_scalar(obj,bounds=(p[0]*.96,p[0]*1.04),method='bounded',options={'xatol':1e-10})
        error=float(abs(opt.x-p[0]));assert error<1e-6
        audit['synthetic'].append(dict(material=material,true_d_um=float(p[0]),recovered_d_um=float(opt.x),error_um=error))
    assert max_matrix<1e-10 and max_series<1e-10
    audit['checks']['matrix_max_reflectance_error']=max_matrix
    audit['checks']['80_pass_max_reflectance_error']=max_series
    for key,fit in r['fits'].items():
        errs=[];direct_difference=[];p=fit['vector']
        for v,y,t in data(fit['material']):
            errs.extend((100*(measured(v,t,p,fit['material'],fit['beams'])-y)).tolist())
            assert np.all(np.isfinite(errs))
            if fit['beams']=='multi':
                physical=reflectance(v,t,p,fit['material']);assert physical.min()>=0 and physical.max()<=1+1e-9
                direct_difference.extend((100*(measured(v,t,p,fit['material'],'two')-measured(v,t,p,fit['material'],'multi'))).tolist())
        rmse=float(np.sqrt(np.mean(np.array(errs)**2)));assert abs(rmse-fit['rmse_pp'])<1e-10
        assert fit['success']
        audit['fits'][key]={'recomputed_rmse_pp':rmse,'n':len(errs)}
        if direct_difference:
            audit['fits'][key]['same_parameters_two_minus_multi_rms_pp']=float(np.sqrt(np.mean(np.array(direct_difference)**2)))
            audit['fits'][key]['same_parameters_two_minus_multi_max_pp']=float(max(abs(np.array(direct_difference))))
    for i in range(1,5):
        a,info=read_data(i);assert len(a)==7469 and np.isfinite(a).all() and (np.diff(a[:,0])>0).all()
        audit['checks'][f'input{i}_over_100_percent']=int((a[:,1]>100).sum())
    audit['status']='passed; implementation and conditional numerical checks, not absolute metrological accuracy'
    r['status']='validated conditional numerical results; optical reference and calibration limitations apply'
    (folder/'results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'validation.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
