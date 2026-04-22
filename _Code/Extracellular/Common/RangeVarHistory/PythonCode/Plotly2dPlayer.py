
# !! don't forget to use the actual x, y and time rather than indices

# !! make sure we have the equal scale by x and y even though dx != dy

# !! try to rewrite this code using plotly.express rather than plotly.graph_objects
#    (for Pyplot3dPlayer, this gave us higher performance)



from Separated.TwoDimPlayerBase import TwoDimPlayerBase

import numpy as np
import plotly.graph_objects as go

from neuron import h


class Plotly2dPlayer(TwoDimPlayerBase):
    
    _palette = 'viridis'
    
    _fig = None
    
    
    def __init__(self, rangeVar_2d, gridSlicerWidget, varNameWithIndexAndUnits, rangeVar_min, rangeVar_max):
        
        numFrames = rangeVar_2d.shape[0]
        
        # Reducing/transposing from (numFrames, numSegms) to (numFrames, nx_screen, ny_screen)
        rangeVar_3d = self.getRangeVarSlice(rangeVar_2d, h.gridOfSections, gridSlicerWidget)
        
        # Create figure
        fig = go.Figure()
        
        xAxisLabel, yAxisLabel = self.getAxisLabels(gridSlicerWidget)
        hovertemplate=(
            f'{xAxisLabel}: %{{x}}<br>'
            f'{yAxisLabel}: %{{y}}<br>'
            f'{varNameWithIndexAndUnits}: %{{z}}<extra></extra>')
        
        # Create and add traces for each frame
        frames = []
        for frameIdx in range(numFrames):
            frame = go.Frame(
                data=[go.Heatmap(
                    z=rangeVar_3d[frameIdx, :, :], 
                    colorscale=self._palette, 
                    zmin=rangeVar_min, 
                    zmax=rangeVar_max,
                    colorbar=dict(title=varNameWithIndexAndUnits),
                    hovertemplate=hovertemplate
                )],
                name=f't={frameIdx}'
            )
            frames.append(frame)
            
        # Add the first frame to the figure
        fig.add_trace(go.Heatmap(
            z=rangeVar_3d[0, :, :], 
            colorscale=self._palette, 
            zmin=rangeVar_min, 
            zmax=rangeVar_max,
            colorbar=dict(title=varNameWithIndexAndUnits),
            hovertemplate=hovertemplate
        ))
        
        # Update layout with slider and animation settings
        fig.update_layout(
            updatemenus=[{
                'buttons': [
                    {
                        'label': 'Start',
                        'method': 'animate',
                        'args': [None, {'frame': {'duration': 100, 'redraw': True},
                                        'fromcurrent': True,
                                        'transition': {'duration': 0}}]
                    },
                    {
                        'label': 'Stop',
                        'method': 'animate',
                        'args': [[None], {'frame': {'duration': 0, 'redraw': True},
                                          'mode': 'immediate',
                                          'transition': {'duration': 0}}]
                    }
                ],
                'pad': {'r': 10, 't': 60},
                'showactive': False,
                'type': 'buttons',
                'x': 0.1,
                'y': 0,
                'xanchor': 'right',
                'yanchor': 'top'
            }],
            sliders=[{
                'active': 0,
                'yanchor': 'top',
                'xanchor': 'left',
                'currentvalue': {
                    'prefix': 'Frame: ',
                    'visible': True,
                    'xanchor': 'right'
                },
                'transition': {'duration': 0},
                'pad': {'b': 10, 't': 50},
                'len': 0.9,
                'x': 0.1,
                'y': 0,
                'steps': [{'args': [[f't={frameIdx}'],
                                    {'frame': {'duration': 100, 'redraw': True},
                                     'mode': 'immediate',
                                     'transition': {'duration': 0}}],
                           'label': str(frameIdx),
                           'method': 'animate'} for frameIdx in range(numFrames)]
            }],
            # Set aspect ratio to 1 for square cells
            # !! it looks like setting only one of them is enough
            xaxis=dict(scaleanchor='y', scaleratio=1),
            yaxis=dict(scaleanchor='x', scaleratio=1)
        )
        
        # Update x and y axis labels
        fig.update_xaxes(title_text=xAxisLabel)
        fig.update_yaxes(title_text=yAxisLabel)
        
        # Add frames to the figure
        fig.frames = frames
        
        self._fig = fig
        
    def show(self):
        
        # Show the figure
        self._fig.show()
        