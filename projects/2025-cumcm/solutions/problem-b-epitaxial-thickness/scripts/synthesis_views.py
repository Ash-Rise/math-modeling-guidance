"""Reader-facing views from frozen fits and recorded candidates; no optimization."""
import json
import numpy as np
import matplotlib.pyplot as plt
from inspect_data import ROOT,read_data
from optics import dielectric
from shared.figure_style import figure_size
from solve import data,initial_thickness

def generate(finish,colors):
    r=json.loads((ROOT/'results/frozen/results.json').read_text(encoding='utf-8'))
    # Both materials use their frozen MULTI model; these are conditional responses.
    fig,axs=plt.subplots(2,2,figsize=figure_size(height=4.5),sharex=True)
    v=np.linspace(450,4000,5000)
    for j,m in enumerate(['SiC','Si']):
        p=r['fits'][m+'_multi']['vector']
        ns=[np.sqrt(e) for e in dielectric(v,p,m)]
        for k,(n,label) in enumerate(zip(ns,['外延层','衬底'])):
            axs[0,j].plot(v,n.real,c=colors[k],ls=['-','--'][k],lw=1.05,label=label)
            axs[1,j].semilogy(v,np.maximum(n.imag,1e-12),c=colors[k],ls=['-','--'][k],lw=1.05)
        axs[0,j].set(title=m,ylabel='折射率实部 n')
        axs[0,j].legend(frameon=False)
        axs[1,j].set(ylabel='消光系数 κ（对数）',xlabel='波数 / cm⁻¹')
        if m=='SiC':
            for ax in axs[:,j]:ax.axvspan(798,970,color='.9',zorder=-1)
    finish(fig,'fig6_dispersion')

    # Reconstruct exactly the stride-8 initialization used by the recorded search.
    fig,axs=plt.subplots(2,2,figsize=figure_size(height=4.8))
    for j,m in enumerate(['SiC','Si']):
        curves=data(m,stride=8);vv,yy,_=curves[0];mask=vv>=1400
        vv=vv[mask];yy=yy[mask]
        base=np.polynomial.Polynomial.fit(vv,yy,3)(vv)
        amp=np.abs(np.fft.rfft((yy-base)*np.hanning(len(vv)),n=8*len(vv)))
        freq=np.fft.rfftfreq(8*len(vv),np.median(np.diff(vv)))
        d=freq*1e4/(2*np.sqrt(6.56 if m=='SiC' else 11.67316))
        mask=(d>=1)&(d<=30);amp=amp/amp[mask].max()
        axs[0,j].plot(d[mask],amp[mask],c=colors[0],lw=.9)
        d0=initial_thickness(curves,m)
        starts=r['fits'][m+'_multi']['coarse_candidates']
        assert np.isclose(starts[1]['start_d_um'],d0,rtol=0,atol=1e-10)
        axs[0,j].axvline(d0,c=colors[1],ls='--',lw=.8)
        axs[0,j].text(.96,.91,f'初值 {d0:.4f} μm',ha='right',transform=axs[0,j].transAxes)
        axs[0,j].set(title=m+'：实际粗算输入的频谱',xlabel='近似厚度坐标 / μm',ylabel='归一化 FFT 幅值')
        # Category positions show coincident solutions without invented jitter in d.
        for k,beam in enumerate(['two','multi']):
            cs=r['fits'][m+'_'+beam]['coarse_candidates']
            x=np.arange(3)+(0 if k==0 else 4)
            for xx,c in zip(x,cs):
                axs[1,j].plot(xx,c['d_um'],marker=['o','s'][k],c=colors[k],ms=4)
                axs[1,j].annotate(f"{c['rmse_pp']:.2f}",(xx,c['d_um']),xytext=(0,7),
                                   textcoords='offset points',ha='center',fontsize=8)
        axs[1,j].set_xticks([0,1,2,4,5,6],['0.85','1','1.15']*2)
        axs[1,j].set(xlabel='左：双光束；右：多光束（初值倍率）',ylabel='粗算终止厚度 / μm')
        axs[1,j].margins(y=.3)
        axs[1,j].text(.02,.96,'点旁数值：RMSE / 百分点',va='top',
                      transform=axs[1,j].transAxes,fontsize=8)
    finish(fig,'fig7_search')

    # Compare only identical full-band, two-angle fitting bases.
    fig,axs=plt.subplots(1,2,figsize=figure_size(height=2.9))
    for ax,m in zip(axs,['SiC','Si']):
        base=r['fits'][m+'_multi']
        rows=[base]+[next(x for x in r['sensitivity'] if x['material']==m and x['scenario']==name)
                     for name in ['zero_offset','free_index']]
        for k,(x,label) in enumerate(zip(rows,['主参考','无常量偏移','自由介电尺度'])):
            assert x['band']==base['band'] and x['angles']==base['angles'] and x['split']=='all'
            ax.scatter(x['d_um'],x['rmse_pp'],c=colors[[0,2,1][k]],marker=['o','s','D'][k],s=24,zorder=3)
            delta=(6,-14) if k==0 else ((6,7) if k==1 else (-6,7))
            ax.annotate(label,(x['d_um'],x['rmse_pp']),xytext=delta,textcoords='offset points',
                        ha='right' if k==2 else 'left',fontsize=8)
        ax.set(title=m,xlabel='条件性厚度 / μm',ylabel='全拟合 RMSE / 百分点')
        ax.margins(x=.3,y=.45)
    finish(fig,'fig8_fit_tradeoff')
