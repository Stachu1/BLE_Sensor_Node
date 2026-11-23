"""Compare S11 and Z of several runs, frequency divided by 1.01 (solder mask shift), BLE shaded.
Usage: [TITLE="..."] python plot_s11_compare.py <out.png> <hash>=<label>[=<shift>] [...]   (shift default 1.01, use 1 for a run with the explicit mask)"""
import sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
out=sys.argv[1]; items=[(x.split('=')+['1.01'])[:3] for x in sys.argv[2:]]
fig,ax=plt.subplots(1,2,figsize=(13,4.8))
for h,lab,k in items:
    a=np.loadtxt('results/runs/%s/S11.csv'%h,delimiter=',',skiprows=1)
    f=a[:,0]/float(k)/1e9
    ax[0].plot(f,a[:,3],label=lab)
    ax[1].plot(f,a[:,4],label=lab+' R'); ax[1].plot(f,a[:,5],'--',color=ax[1].lines[-1].get_color(),label=lab+' X')
for x in ax:
    x.axvspan(2.400,2.4835,color='0.85',zorder=0); x.set_xlim(2.1,2.8); x.grid(alpha=.4); x.set_xlabel('frequency (GHz), simulated / shift (solder mask, 1.01 unless noted)')
ax[0].axhline(-10,color='k',lw=.8); ax[0].set_ylabel('S11 (dB) at the feed notch, no parts'); ax[0].set_ylim(-20,0); ax[0].legend(fontsize=8)
ax[1].axhline(50,color='k',lw=.8); ax[1].set_ylabel('Z (ohm)'); ax[1].set_ylim(-150,250); ax[1].legend(fontsize=7,ncol=2)
import os; fig.suptitle(os.environ.get('TITLE','BSN-N52 straight IFA, feed at KiCad x 143, keep-out 24 mm wide, height 4 / 5 / 6 mm (grey = BLE)'))
fig.tight_layout(); fig.savefig(out,dpi=110); print(out)
