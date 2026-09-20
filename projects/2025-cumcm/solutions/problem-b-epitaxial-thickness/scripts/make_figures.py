"""Paper figures, derived from frozen parameters without refitting."""
import json,warnings,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from inspect_data import ROOT,read_data,FIGURE_COLORS as C
from optics import measured,amplitudes

warnings.filterwarnings('error',message='Glyph .* missing from font')
sys.path.insert(0,str(ROOT.parents[3]))
from shared.figure_style import paper_style,figure_size,save_figure
OUT=ROOT/'figures'

def finish(fig,name):
    fig.tight_layout(pad=.8,rect=(0,0,1,.94) if fig.legends else (0,0,1,1))
    save_figure(fig,OUT/f'{name}.png')
    plt.close(fig)

def generate_figures():
    OUT.mkdir(exist_ok=True);r=json.loads((ROOT/'results/frozen/results.json').read_text())
    arrays={i:read_data(i)[0] for i in range(1,5)}
    fig,axs=plt.subplots(2,1,figsize=figure_size(height=4.5),sharex=True)
    for ax,material,ids in zip(axs,['SiC','Si'],[(1,2),(3,4)]):
        for j,i in enumerate(ids):ax.plot(arrays[i][:,0],arrays[i][:,1],c=C[j],ls=['-','--'][j],lw=.95,label=f'{[10,15][j]}°，附件{i}')
        ax.axvspan(399,450,color='.85',zorder=-1);ax.set(ylabel='反射率 / %',title=material)
        ax.legend(loc='upper right',frameon=False)
    axs[0].axhline(100,color='.45',ls=':',lw=.6)
    axs[-1].set_xlabel('波数 / cm⁻¹');finish(fig,'fig1_measured_spectra')

    fig,axs=plt.subplots(3,2,figsize=figure_size(height=5.5))
    for j,i in enumerate([1,2]):
        a=arrays[i];v=a[:,0];theta=[10,15][j]
        for row,band in enumerate([(1100,4000),(930,1020)]):
            mask=(v>=band[0])&(v<=band[1])
            axs[row,j].plot(v[mask],a[mask,1],c='.15',lw=.85,label='实测')
            for k,beam in enumerate(['two','multi']):
                pred=100*measured(v,theta,r['fits']['SiC_'+beam]['vector'],'SiC',beam)
                axs[row,j].plot(v[mask],pred[mask],c=C[k],lw=1.05,ls=['--','-'][k],
                                label=['双光束','多光束'][k])
        for k,beam in enumerate(['two','multi']):
            mask=(v>=450)&(v<=4000)
            pred=100*measured(v,theta,r['fits']['SiC_'+beam]['vector'],'SiC',beam)
            axs[2,j].plot(v[mask],pred[mask]-a[mask,1],c=C[k],lw=1.05,ls=['--','-'][k])
        axs[0,j].set(title=f'{theta}°：透光区',ylabel='反射率 / %')

        if j==0:fig.legend(*axs[0,j].get_legend_handles_labels(),loc='upper center',ncol=3)
        axs[1,j].set(title='共振边缘局部',ylabel='反射率 / %')
        axs[2,j].axhline(0,c='.5',lw=.5)
        axs[2,j].set(ylabel='拟合 − 实测 / 百分点')
        for ax in axs[:,j]:ax.set_xlabel('波数 / cm⁻¹')
    finish(fig,'fig2_sic_fit_residual')

    fig,axs=plt.subplots(2,2,figsize=figure_size(height=4.8))
    for j,i in enumerate([3,4]):
        a=arrays[i];v=a[:,0];theta=[10,15][j];mask=(v>=450)&(v<=1900)
        axs[0,j].plot(v[mask],a[mask,1],color='.15',lw=.9,label='实测')
        for k,beam in enumerate(['two','multi']):
            pred=100*measured(v,theta,r['fits']['Si_'+beam]['vector'],'Si',beam)
            axs[0,j].plot(v[mask],pred[mask],c=C[k],ls=['--','-'][k],lw=1.05,label=['双光束','多光束'][k])
            allmask=(v>=450)&(v<=4000)
            axs[1,j].plot(v[allmask],pred[allmask]-a[allmask,1],c=C[k],ls=['--','-'][k],lw=1.05)
        axs[0,j].set(title=f'{theta}°：主要干涉条纹',ylabel='反射率 / %')

        if j==0:fig.legend(*axs[0,j].get_legend_handles_labels(),loc='upper center',ncol=3)
        axs[1,j].axhline(0,color='.4',lw=.5);axs[1,j].set(ylabel='拟合 − 实测 / 百分点')
        for ax in axs[:,j]:ax.set_xlabel('波数 / cm⁻¹')
    finish(fig,'fig3_si_two_vs_multi')

    fig,axs=plt.subplots(2,2,figsize=figure_size(height=4.6))
    for col,material in enumerate(['SiC','Si']):
        p=r['fits'][material+'_multi']['vector'];v=np.linspace(450,4000,2000)
        for j,t in enumerate([10,15]):
            rho=np.max(np.array([abs(h) for _,_,h in amplitudes(v,t,p,material)]),axis=0)
            axs[0,col].semilogy(v,rho,c=C[j],ls=['-','--'][j],lw=1.05,label=f'{t}°')
            diff=100*(measured(v,t,p,material,'two')-measured(v,t,p,material,'multi'))
            axs[1,col].plot(v,diff,c=C[j],ls=['-','--'][j],lw=1.05)
        axs[0,col].set(title=material,ylabel='往返振幅比 ρ');axs[0,col].legend(frameon=False)
        axs[1,col].set(ylabel='双束 − 多束 / 百分点')
        axs[1,col].axhline(0,color='.5',lw=.5)
        for ax in axs[:,col]:ax.set_xlabel('波数 / cm⁻¹')
    finish(fig,'fig4_multibeam_mechanism')

    labels={'10deg':'仅10°','15deg':'仅15°','zero_offset':'仅乘性校准','free_index':'自由介电尺度（对照）',
            's_polarized':'纯s偏振','p_polarized':'纯p偏振','zero_epi_drude':'外延层Drude项置零',
            '6H_reference':'6H参考色散','transparent_band':'透光频段（SiC）','middle_band':'600—3500 cm⁻¹（Si）'}
    fig,axs=plt.subplots(1,2,figsize=figure_size(height=4.1),sharey=True)
    for ax,material in zip(axs,['SiC','Si']):
        rows={s['scenario']:s for s in r['sensitivity'] if s['material']==material}
        base=r['fits'][material+'_multi']['d_um']
        ax.axvline(base,c='.45',ls='--',lw=.9,label='主结果')
        for i,key in enumerate(labels):
            if key not in rows:
                ax.text(.5,i,'不适用',transform=ax.get_yaxis_transform(),ha='center',va='center',color='.4',fontsize=8)
                continue
            ax.plot(rows[key]['d_um'],i,marker='D' if key=='free_index' else 'o',ms=4,
                    c=C[1] if key=='free_index' else C[0])
        ax.set_yticks(range(len(labels)),labels.values())
        ax.set(title=material,xlabel='条件性厚度 / μm');ax.tick_params(axis='y',length=0)
        ax.grid(axis='x');ax.legend(loc='lower right')
    axs[0].set_ylim(len(labels)-.5,-.5)
    finish(fig,'fig5_sensitivity')
    from synthesis_views import generate
    generate(finish,C)
    print('Generated 8 evidence figures without optimization.')

def main():
    with paper_style():
        generate_figures()

if __name__=='__main__':main()
