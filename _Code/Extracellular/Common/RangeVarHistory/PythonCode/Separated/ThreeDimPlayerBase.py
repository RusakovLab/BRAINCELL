

# !! if the range equals 0, think about making 0.5 opacity everywhere (or the middle colour of the colourbar)


class ThreeDimPlayerBase:
    
    def makeZeroToOne(self, rangeVar, rangeVar_min, rangeVar_max):
        
        # Make a linear transformation of the data to fit [0, 1] range
        
        rangeVar_rangeOr1 = rangeVar_max - rangeVar_min
        if rangeVar_rangeOr1 == 0:
            # Just to avoid division by 0 below (however, pyplot will print UserWarning-s anyway)
            # UPD: maybe the UserWarning-s were fixed for pyplot - need to retest
            rangeVar_rangeOr1 = 1
            
        # !! maybe do it with only one pass for better performance
        rangeVar0To1 = (rangeVar - rangeVar_min) / rangeVar_rangeOr1
        
        return rangeVar0To1, rangeVar_rangeOr1
        