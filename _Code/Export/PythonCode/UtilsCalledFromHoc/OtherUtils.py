from neuron import h
import re

from Utils.OtherUtils import getAllSectionNamesExceptNanogeometry


_EXTRA_CELL_SEC_NAME_RE = re.compile(r'^_pysec\.EXTRA_CELL_\d+\.')


def _isExtraCellSectionName(name):
    return bool(_EXTRA_CELL_SEC_NAME_RE.match(name))


def checkForNotImplementedExportScenario():
    if h.name_declared('gridOfSections') and h.gridOfSections is not None:
        h.mwh.showNotImplementedWarning('Cannot export the cell with the sections grid deployed.')
        return 1
    secNames = getAllSectionNamesExceptNanogeometry()
    unknownDotSecs = [
        secName.s for secName in secNames
        if '.' in secName.s and not _isExtraCellSectionName(secName.s)
    ]
    isNotImpl = len(unknownDotSecs) > 0
    if isNotImpl:
        h.mwh.showNotImplementedWarning(
            'Cannot export the cell because some sections were created inside HOC templates or in Python.')
        # !! notes regarding the sections created in Python:
        #       * they can be owned by a class (e.g. "_pysec.<ExtraCell.ExtraCell object at 0x00000173A26CEC70>.soma") or not (e.g. "_pysec.soma");
        #       * it's allowed to create 2+ sections with the same name;
        #       * it's allowed to use the most arbitrary string as a section name
        #       * when the name arg is not passed to h.Section ctor explicitly, NEURON names the new sec in style "_pysec.__nrnsec_000002874b2c7560"
    return isNotImpl


