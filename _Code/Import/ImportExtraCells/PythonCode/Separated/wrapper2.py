
import pickle

from ThirdParty.hoc2swc import hoc2swc

with open('temp.pickle', 'rb') as f:
    data = pickle.load(f)
    
# !! maybe delete "temp.pickle" at this point

hocFilePathName = data['hocFilePathName']
swcFilePathName = data['swcFilePathName']

# !! maybe specify these default args: mod_path=None, no_mod=False
#    (especially when loading "BrainCell Export" HOC file from a folder which doesn't contain "nrnmech.dll")

# !! maybe modify "hoc2swc" to optimize converting our old-style astrocyte HOC files to SWC
#    (currently it creates a lot of secondary SWC files which we just ignore)

hoc2swc(hocFilePathName, swcFilePathName, separate_process=False)
