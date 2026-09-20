"""Reproduce conditional Fresnel inversions and report sensitivity, not fake CIs."""
from pathlib import Path
import argparse,json,time,sys,platform
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.signal import savgol_filter
from inspect_data import ROOT,read_data
from optics import measured,amplitudes,NAMES

def data(material,band=(450,4000),stride=1,angles=(10,15),split='all'):
    out=[]
    for i,angle in ([(1,10),(2,15)] if material=='SiC' else [(3,10),(4,15)]):
        if angle not in angles:continue
        a,_=read_data(i)
        a=a[(a[:,0]>=band[0])&(a[:,0]<=band[1])][::stride]
        if split!='all':
            hold=(np.floor((a[:,0]-450)/50).astype(int)%5)==0
            a=a[hold if split=='test' else ~hold]
        out.append((a[:,0],a[:,1]/100,angle))
    return out

def initial_thickness(curves,material):
    v,y,_=curves[0];mask=v>=1400
    v=v[mask];y=y[mask]
    # Detrending removes smooth reflectance; FFT only supplies a starting basin.
    baseline=np.polynomial.Polynomial.fit(v,y,3)(v)
    n=np.sqrt(6.56) if material=='SiC' else np.sqrt(11.67316)
    f=np.fft.rfftfreq(8*len(v),np.median(np.diff(v)))
    power=abs(np.fft.rfft((y-baseline)*np.hanning(len(v)),n=8*len(v)))
    d=f*1e4/(2*n)
    valid=(d>=1)&(d<=30)
    return float(d[np.where(valid)[0][np.argmax(power[valid])]])

def fit_model(material,beams,*,band=(450,4000),stride=1,angles=(10,15),
              reference='4H',free_scale=False,offset=True,polarization='unpolarized',
              split='all',start=None,multistart=False,zero_epi=False):
    curves=data(material,band,stride,angles,split)
    d0=initial_thickness(curves,material)
    p0=np.array([d0,3.,100.,1000.,450. if material=='SiC' else 1600.,600.,1.,1.,1.08,0.,0.])
    if start is not None:p0=np.array(start,float)
    lo=np.array([.2,.02,0.,.1,0.,.1,.65,.4,.4,-.15,-.15])
    hi=np.array([50.,100.,5000.,50000.,5000.,50000.,1.4,1.8,1.8,.15,.15])
    free=np.ones(11,bool)
    if not free_scale:free[6]=False;p0[6]=1.
    if material=='Si':free[1]=False;p0[1]=0.
    if not offset:free[9:]=False;p0[9:]=0.
    if zero_epi:free[2:4]=False;p0[2:4]=[0.,1000.]
    for j,angle in enumerate((10,15)):
        if angle not in angles:free[7+j]=free[9+j]=False
    def unpack(x):
        p=p0.copy();p[free]=x;return p
    def residual(x):
        p=unpack(x)
        return np.concatenate([measured(v,t,p,material,beams,reference,polarization)-y for v,y,t in curves])
    candidates=[];best=None
    starts=[.85,1.,1.15] if multistart else [1.]
    for factor in starts:
        trial=p0.copy();trial[0]*=factor
        t0=time.perf_counter()
        fit=least_squares(residual,trial[free],bounds=(lo[free],hi[free]),x_scale='jac',
                          max_nfev=350,ftol=2e-9,xtol=2e-9,gtol=2e-8)
        cand=dict(start_d_um=float(trial[0]),d_um=float(unpack(fit.x)[0]),
                  rmse_pp=float(100*np.sqrt(np.mean(fit.fun**2))),success=bool(fit.success),nfev=fit.nfev)
        candidates.append(cand)
        if best is None or fit.cost<best.cost:best=fit
    p=unpack(best.x)
    bounds_active=[NAMES[i] for i in np.where(free)[0] if abs(p[i]-lo[i])<1e-5 or abs(p[i]-hi[i])<1e-5]
    diagnostics=[]
    for v,y,t in curves:
        pred=measured(v,t,p,material,beams,reference,polarization)
        residuals=(pred-y)*100
        rho=np.max(np.array([abs(h) for _,_,h in amplitudes(v,t,p,material,reference,polarization)]),axis=0)
        diagnostics.append(dict(angle=t,n=len(v),rmse_pp=float(np.sqrt(np.mean(residuals**2))),
            max_abs_residual_pp=float(max(abs(residuals))),rho_max=float(max(rho)),rho_median=float(np.median(rho)),
            residual_lag1=float(np.corrcoef(residuals[:-1],residuals[1:])[0,1])))
    out=dict(material=material,beams=beams,band=list(band),stride=stride,angles=list(angles),
             reference=reference,free_scale=free_scale,offset=offset,polarization=polarization,
             split=split,zero_epi=zero_epi,parameters=dict(zip(NAMES,map(float,p))),vector=p.tolist(),
             d_um=float(p[0]),rmse_pp=float(100*np.sqrt(np.mean(best.fun**2))),success=bool(best.success),
             active_bounds=bounds_active,candidates=candidates,diagnostics=diagnostics)
    return out

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='results/current');parser.add_argument('--quick',action='store_true')
    args=parser.parse_args();folder=ROOT/args.output;folder.mkdir(parents=True,exist_ok=True)
    result=dict(status='computed conditional results, awaiting validation',decision='B01',
                environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform()),fits={},sensitivity=[])
    def save():
        (folder/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    stride=6 if args.quick else 1
    for material in ['SiC','Si']:
        for beams in ['two','multi']:
            coarse=fit_model(material,beams,stride=8,multistart=True)
            fit=fit_model(material,beams,stride=stride,start=coarse['vector'])
            fit['coarse_candidates']=coarse['candidates'];key=f'{material}_{beams}'
            result['fits'][key]=fit;save();print(key,fit['d_um'],fit['rmse_pp'],fit['active_bounds'],flush=True)
    if args.quick:return
    for material in ['SiC','Si']:
        start=result['fits'][material+'_multi']['vector']
        scenarios=[('stride2',dict(stride=2)),('10deg',dict(angles=(10,))),('15deg',dict(angles=(15,))),
                   ('zero_offset',dict(offset=False)),('free_index',dict(free_scale=True)),
                   ('s_polarized',dict(polarization='s')),('p_polarized',dict(polarization='p')),
                   ('zero_epi_drude',dict(zero_epi=True)),('blocked_train',dict(split='train'))]
        if material=='SiC':scenarios += [('6H_reference',dict(reference='6H')),('transparent_band',dict(band=(1100,4000)))]
        else:scenarios += [('middle_band',dict(band=(600,3500)))]
        for name,kw in scenarios:
            fit=fit_model(material,'multi',start=start,**kw)
            fit['scenario']=name
            if name=='blocked_train':
                test=data(material,split='test');p=fit['vector']
                fit['test_rmse_pp']=float(100*np.sqrt(np.mean(np.concatenate([measured(v,t,p,material)-y for v,y,t in test])**2)))
                two=fit_model(material,'two',start=result['fits'][material+'_two']['vector'],split='train')
                p=two['vector'];fit['two_test_rmse_pp']=float(100*np.sqrt(np.mean(np.concatenate([measured(v,t,p,material,'two')-y for v,y,t in test])**2)))
                fit['two_train']=two
            result['sensitivity'].append(fit);save();print(material,name,fit['d_um'],fit['rmse_pp'],fit['active_bounds'],flush=True)
    save()

if __name__=='__main__':main()
