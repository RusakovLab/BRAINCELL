# =============================================================================
#  plots/user_sim_plot.py
#  ─────────────────────────────────────────────────────────────────────────────
#  Standalone matplotlib script launched as a subprocess by SimUserTemplate.
#  NEURON passes the recorded data via a temporary pickle file.
#
#  This script runs in a SEPARATE Python process so the matplotlib window
#  does not block NEURON's GUI event loop.
#  This matches the existing BrainCell pattern (PyplotSubProcHelper).
#
#  HOW IT IS CALLED (from SimUserTemplate._launchPlotSubprocess):
#      python.exe  user_sim_plot.py  <path_to_pickle_file>
#
#  PICKLE FILE CONTENTS (dict):
#      t           list[float]   time vector (ms)
#      v           list[float]   somatic voltage vector (mV)
#      iclamp_amp  float         injected current amplitude (nA)
#      iclamp_delay float        current onset delay (ms)
#      iclamp_dur  float         current duration (ms)
#      tstop       float         total simulation time (ms)
#
#  TO CUSTOMISE THIS PLOT:
#    • Add more subplots (e.g. ax2 for a second variable)
#    • Change colours, line styles, axis limits
#    • Add a second curve (e.g. ion concentration) from extra pickle keys
#    • Save the figure automatically by uncommenting the savefig line
# =============================================================================

import sys
import os
import pickle
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Use a non-interactive backend so this works even without a display server.
# 'TkAgg' is the default on Windows with Anaconda; change to 'Qt5Agg' if needed.
matplotlib.use('TkAgg')


# ── Load data from pickle file ─────────────────────────────────────────────────

if len(sys.argv) < 2:
    print("[user_sim_plot] ERROR: no pickle file path provided as argument.")
    sys.exit(1)

pickleFilePath = sys.argv[1]

if not os.path.exists(pickleFilePath):
    print(f"[user_sim_plot] ERROR: pickle file not found: {pickleFilePath}")
    sys.exit(1)

with open(pickleFilePath, 'rb') as f:
    data = pickle.load(f)

t            = data['t']
v            = data['v']
iclamp_amp   = data['iclamp_amp']
iclamp_delay = data['iclamp_delay']
iclamp_dur   = data['iclamp_dur']
tstop        = data['tstop']


# ── Build the current trace for the lower subplot ─────────────────────────────
# Reconstruct a square-pulse current waveform matching the IClamp parameters.

i_trace = []
for ti in t:
    if iclamp_delay <= ti <= iclamp_delay + iclamp_dur:
        i_trace.append(iclamp_amp)
    else:
        i_trace.append(0.0)


# ── Figure layout ─────────────────────────────────────────────────────────────

fig, (ax_v, ax_i) = plt.subplots(
    nrows=2, ncols=1,
    figsize=(9, 6),
    sharex=True,
    gridspec_kw={'height_ratios': [3, 1]},
    constrained_layout=False)

fig.subplots_adjust(hspace=0.08, top=0.93, bottom=0.11, left=0.1, right=0.97)

fig.patch.set_facecolor('#1C1C2E')
for ax in (ax_v, ax_i):
    ax.set_facecolor('#1C1C2E')
    ax.tick_params(colors='#CCCCCC', labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor('#444466')


# ── Top panel: membrane voltage ───────────────────────────────────────────────

ax_v.plot(t, v, color='#00CFFF', linewidth=1.4, label='V soma (mV)')
ax_v.set_ylabel('Membrane voltage  (mV)', color='#CCCCCC', fontsize=10)
ax_v.yaxis.label.set_color('#CCCCCC')
ax_v.set_title(
    'BrainCell — User Simulation: Current step → Somatic voltage',
    color='#FFFFFF', fontsize=11, pad=10)

# Shade the current injection window
ax_v.axvspan(
    iclamp_delay, iclamp_delay + iclamp_dur,
    alpha=0.08, color='#FF9900', label='IClamp window')

ax_v.legend(
    handles=[
        mpatches.Patch(color='#00CFFF', label='V soma (mV)'),
        mpatches.Patch(color='#FF9900', alpha=0.4, label='IClamp window'),
    ],
    facecolor='#2A2A3E', edgecolor='#444466',
    labelcolor='#CCCCCC', fontsize=9,
    loc='upper right')

ax_v.grid(True, linestyle='--', linewidth=0.4, color='#333355', alpha=0.7)


# ── Bottom panel: injected current ────────────────────────────────────────────

ax_i.plot(t, i_trace, color='#FF9900', linewidth=1.2, label='IClamp (nA)')
ax_i.set_ylabel('Current  (nA)', color='#CCCCCC', fontsize=10)
ax_i.set_xlabel('Time  (ms)',    color='#CCCCCC', fontsize=10)
ax_i.yaxis.label.set_color('#CCCCCC')
ax_i.xaxis.label.set_color('#CCCCCC')
ax_i.set_ylim(
    min(i_trace) - abs(iclamp_amp) * 0.5,
    max(i_trace) + abs(iclamp_amp) * 1.5)
ax_i.grid(True, linestyle='--', linewidth=0.4, color='#333355', alpha=0.7)


# ── Annotation: simulation parameters ─────────────────────────────────────────

param_text = (
    f"amp = {iclamp_amp} nA     "
    f"delay = {iclamp_delay} ms     "
    f"dur = {iclamp_dur} ms     "
    f"tstop = {tstop} ms"
)
fig.text(
    0.5, 0.01, param_text,
    ha='center', fontsize=8,
    color='#888899',
    style='italic')


# ── Optional: auto-save figure ────────────────────────────────────────────────
# Uncomment the line below to save a PNG next to the pickle file automatically.
# fig.savefig(pickleFilePath.replace('.pkl', '.png'), dpi=150, bbox_inches='tight')


# ── Show ──────────────────────────────────────────────────────────────────────

plt.show()
