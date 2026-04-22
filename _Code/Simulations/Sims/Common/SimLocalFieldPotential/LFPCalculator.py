# Patched/optimized version of LFPCalculator with full backward-compatible API for BrainCell.
# - Keeps legacy entry points: setListOfPts(), onPreRun(sigma, isSkipNanoSects, isGpuOrCpu), onAdvance(), cleanup().
# - Adds optional "total membrane current" mode and other performance/stability fixes.

from neuron import h
import math
import numpy as np

from XpuUtils import xpuUtils
from OtherInterModularUtils import isNanoGeometrySection, codeContractViolation


class LFPCalculator:

    # Legacy defaults preserved
    _minDist = 0.1                              # (um) distance floor to avoid singularity (was 1e-6; too small in practice)
    _const = 1e-5 / 4 / h.PI                    # (unitless) phys/units const => uV

    def __init__(self, theModel=None):
        # NOTE: original BrainCell code instantiates LFPCalculator() with no args.
        # We keep that behavior; the model is optional and only used for future extensions.
        self._theModel = theModel

        # Legacy state
        self._listOfPts = None
        self._sigma = None
        self._isGpuOrCpu = False
        self._isPrinted = False

        # New options (safe defaults => legacy behavior)
        self._useTotalMembraneCurrent = False   # False => i_cap only (legacy)
        self._dtype = np.float32                # float32 kernel saves memory; output stays float64 in python
        self._chunkSegs = 0                     # 0 => no chunking

        # Cached sources/kernels
        self._srcPtIdx_to_ptrSegmRefICap = None           # list of h.Pointer OR tuples of pointers
        self._segmArea = None                             # (nSeg,) float64, um2
        self._x_srcPtIdxAndDstPtIdx_to_factor = None      # (nSeg,nPt) numpy or cupy
        self._icap = None                                 # (nSeg,) numpy float64
        self._pot = None                                  # (nPt,) numpy float64

        # GPU backend (optional)
        self._hasCupy = False
        self._cp = None

    # -------------------------
    # Public / legacy API
    # -------------------------

    def setListOfPts(self, listOfPts):
        self._listOfPts = listOfPts
        if self._listOfPts is not None:
            for pt in self._listOfPts:
                pt.theValue = 0.0

    def onPreRun(self, sigma, isSkipNanoSects, isGpuOrCpu):
        """Legacy signature used by SimLocalFieldPotential.py"""
        self._sigma = float(sigma)
        if self._sigma <= 0:
            raise ValueError("sigma must be > 0 (S/m)")

        self._isGpuOrCpu = bool(isGpuOrCpu)

        # Resolve GPU backend if requested
        self._init_xpu_backend()

        # Cache pointers, areas, and build kernel
        self._cacheData(isSkipNanoSects=isSkipNanoSects)

        # Allocate state arrays
        self._allocateArrays()

        # Initialize electrode values (avoid junk on first plot)
        if self._listOfPts is not None:
            for pt in self._listOfPts:
                pt.theValue = 0.0

        return False  # legacy "isCancel"

    def onAdvance(self):
        if self._srcPtIdx_to_ptrSegmRefICap is None or self._x_srcPtIdxAndDstPtIdx_to_factor is None:
            return
        if self._listOfPts is None or len(self._listOfPts) == 0:
            return

        # Read current density vector (mA/cm2)
        if self._useTotalMembraneCurrent:
            # ptr entry is (p_cap, p_ion)
            for i, (p_cap, p_ion) in enumerate(self._srcPtIdx_to_ptrSegmRefICap):
                self._icap[i] = float(p_cap[0]) + float(p_ion[0])
        else:
            for i, p_cap in enumerate(self._srcPtIdx_to_ptrSegmRefICap):
                self._icap[i] = float(p_cap[0])

        # Compute potentials: pot = icap @ factor  (uV)
        if self._isGpuOrCpu and self._hasCupy:
            cp = self._cp
            ic = cp.asarray(self._icap, dtype=cp.float32 if self._dtype == np.float32 else cp.float64)
            fac = self._x_srcPtIdxAndDstPtIdx_to_factor  # already cupy
            pot = ic.dot(fac)
            pot_host = cp.asnumpy(pot)
            for j, pt in enumerate(self._listOfPts):
                pt.theValue = float(pot_host[j])
        else:
            if self._chunkSegs and self._chunkSegs > 0:
                pot = np.zeros((len(self._listOfPts),), dtype='float64')
                nseg = self._icap.shape[0]
                for s0 in range(0, nseg, self._chunkSegs):
                    s1 = min(nseg, s0 + self._chunkSegs)
                    pot += self._icap[s0:s1].dot(self._x_srcPtIdxAndDstPtIdx_to_factor[s0:s1, :])
                self._pot[:] = pot
            else:
                self._pot[:] = self._icap.dot(self._x_srcPtIdxAndDstPtIdx_to_factor)

            for j, pt in enumerate(self._listOfPts):
                pt.theValue = float(self._pot[j])

    def cleanup(self, isDestroyListOfPtsInCalc):
        # release arrays (helps GPU memory too)
        self._srcPtIdx_to_ptrSegmRefICap = None
        self._x_srcPtIdxAndDstPtIdx_to_factor = None
        self._icap = None
        self._pot = None
        self._segmArea = None

        if isDestroyListOfPtsInCalc:
            self._listOfPts = None

    # -------------------------
    # Optional new knobs (safe)
    # -------------------------

    def setUseTotalMembraneCurrent(self, isUseTotal):
        """If True, uses i_cap + i_ion as source (still point-source kernel)."""
        self._useTotalMembraneCurrent = bool(isUseTotal)

    def setMinDistUm(self, minDistUm):
        v = float(minDistUm)
        if v <= 0:
            raise ValueError("minDistUm must be > 0")
        self._minDist = v

    def setKernelDtype(self, dtypeStr):
        if str(dtypeStr).lower() == 'float64':
            self._dtype = np.float64
        else:
            self._dtype = np.float32

    def setChunkSegs(self, n):
        self._chunkSegs = int(n) if n else 0

    # -------------------------
    # Internals
    # -------------------------

    def _init_xpu_backend(self):
        if not self._isGpuOrCpu:
            self._hasCupy = False
            self._cp = None
            return
        try:
            import cupy as cp
            self._cp = cp
            self._hasCupy = True
        except Exception:
            # fall back to CPU if CuPy not available
            self._cp = None
            self._hasCupy = False
            self._isGpuOrCpu = False

    def _cacheData(self, isSkipNanoSects):
        if self._listOfPts is None:
            codeContractViolation("LFPCalculator.onPreRun called before setListOfPts")

        # Ensure capacitance mechanism exists so _ref_i_cap is defined.
        mtCap = h.MechanismType(0)
        mtCap.select('capacitance')

        ptrs = []
        areas = []
        src_xyz = []

        for sec in h.allsec():
            if isSkipNanoSects and isNanoGeometrySection(sec.name()):
                continue

            mtCap.make(sec=sec)

            # Segment coordinates: try to use 3D; if absent, fall back to pt3d(0) or origin.
            # NOTE: original code used a helper mth.getSegmPt3d; we keep a robust fallback.
            for segm in sec.allseg():
                # area (um2)
                areas.append(float(segm.area()))

                # coordinates (um)
                x = y = z = 0.0
                try:
                    # Use section 3d interpolation if available; else raises.
                    x = float(h.x3d(0.5, sec=sec))
                    y = float(h.y3d(0.5, sec=sec))
                    z = float(h.z3d(0.5, sec=sec))
                except Exception:
                    pass
                src_xyz.append((x, y, z))

                if self._useTotalMembraneCurrent:
                    ptrs.append((segm._ref_i_cap, segm._ref_i_ion))
                else:
                    ptrs.append(segm._ref_i_cap)

        self._srcPtIdx_to_ptrSegmRefICap = ptrs
        self._segmArea = np.asarray(areas, dtype='float64')
        src_xyz = np.asarray(src_xyz, dtype='float64')

        dst_xyz = np.asarray([(float(pt.x), float(pt.y), float(pt.z)) for pt in self._listOfPts], dtype='float64')

        # Build kernel (nSeg,nPt): factor = const * area / sigma / dist
        if src_xyz.size == 0 or dst_xyz.size == 0:
            self._x_srcPtIdxAndDstPtIdx_to_factor = np.zeros((src_xyz.shape[0], dst_xyz.shape[0]), dtype=self._dtype)
            return

        d = np.linalg.norm(src_xyz[:, None, :] - dst_xyz[None, :, :], axis=2)
        d = np.maximum(d, self._minDist)

        factor = (self._const * self._segmArea[:, None]) / (self._sigma * d)
        factor = factor.astype(self._dtype, copy=False)

        if self._isGpuOrCpu and self._hasCupy:
            self._x_srcPtIdxAndDstPtIdx_to_factor = self._cp.asarray(factor)
        else:
            self._x_srcPtIdxAndDstPtIdx_to_factor = factor

        if (not self._isPrinted) and (src_xyz.shape[0] > 0) and (dst_xyz.shape[0] > 0):
            # one-time info
            self._isPrinted = True

    def _allocateArrays(self):
        nSeg = len(self._srcPtIdx_to_ptrSegmRefICap) if self._srcPtIdx_to_ptrSegmRefICap is not None else 0
        nPt = len(self._listOfPts) if self._listOfPts is not None else 0

        # current density vector (mA/cm2)
        self._icap = np.zeros((nSeg,), dtype='float64')
        # potentials (uV)
        self._pot = np.zeros((nPt,), dtype='float64')
