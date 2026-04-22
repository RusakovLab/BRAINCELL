
# !! BUGs:
#    * the markers for distant points are shown in front of the markers for close points
#    * the markers don't change their size on scaling the scene
#    * too many ticks on the slider for real records
#    * when isOpacitiesOrColours is True, the animation preparation stage takes too much time
#    * when isOpacitiesOrColours is True, the slider shows frameIdx rather than "t (ms)"
#    * !! (?) when isOpacitiesOrColours is True, if clicking "Stop", it has some inertia before the actual stop
#    * when isOpacitiesOrColours is False, the garbage in the last digits of the label "t (ms)=..." and the slider tick labels

# https://plotly.com/python/3d-scatter-plots/
# https://plotly.com/python/animations/

from Separated.ThreeDimPlayerBase import ThreeDimPlayerBase

import plotly.graph_objects as go
import plotly.express as px

import pandas as pd
import numpy as np


class Plotly3dPlayer(ThreeDimPlayerBase):
    
    _markerSize = 20
    
    # Used only when isOpacitiesOrColours is True
    _markerColour = '0, 0, 255'
    
    # Used only when isOpacitiesOrColours is False
    _opacity = 0.25
    _palette = 'viridis'
    
    
    _fig = None
    
    
    def __init__(self, x, y, z, rangeVar, t, varNameWithIndexAndUnits, isOpacitiesOrColours, rangeVar_min, rangeVar_max):
        
        if isOpacitiesOrColours:
            numFrames = len(t)
            fig = self._initForOpacities(x, y, z, rangeVar, numFrames, varNameWithIndexAndUnits, rangeVar_min, rangeVar_max)
        else:
            fig = self._initForColours(x, y, z, rangeVar, t, varNameWithIndexAndUnits, rangeVar_min, rangeVar_max)
            
        # Set the aspect ratio to 'data' to preserve proportions
        fig.update_scenes(aspectmode='data')
        
        # Customize the axis labels
        fig.update_layout(scene=dict(xaxis_title='x (μm)', yaxis_title='y (μm)', zaxis_title='z (μm)'))
        
        # Customize the figure title
        fig.update_layout(title=varNameWithIndexAndUnits)
        
        self._fig = fig
        
    def show(self):
        
        # Show the Plotly figure
        self._fig.show()
        
        
    def _initForOpacities(self, x, y, z, rangeVar, numFrames, varNameWithIndexAndUnits, rangeVar_min, rangeVar_max):
        
        # Make a linear transformation of the data to fit [0, 1] range
        rangeVar0To1, _ = self.makeZeroToOne(rangeVar, rangeVar_min, rangeVar_max)
        
        # Create initial figure with a single trace
        fig = go.Figure(data=self._getOneFrameForOpacities(x, y, z, rangeVar0To1[0]))
        
        # Creating frames for the animation
        frames = []
        for frameIdx in range(numFrames):
            frames.append(go.Frame(
                data=self._getOneFrameForOpacities(x, y, z, rangeVar0To1[frameIdx]),    # !! reuse the very first frame we created just above
                name=str(frameIdx)
            ))
        fig.frames = frames
        
        # Define a slider for the animation
        sliders = [{
            'pad': {'b': 10, 't': 60},
            'len': 0.9,
            'x': 0.1,
            'y': 0,
            'steps': [{'args': [[f.name], {'frame': {'duration': 0, 'redraw': True}, 'mode': 'immediate', 'fromcurrent': True}],
                       'label': f.name,
                       'method': 'animate'} for f in frames]
        }]
        
        # Add Start and Stop buttons
        updatemenus = [{
            'type': 'buttons',
            'showactive': False,
            'x': 0.1,
            'y': 0,
            'xanchor': 'right',
            'yanchor': 'top',
            'pad': {'r': 10, 't': 60},
            'buttons': [
                {
                    'label': 'Start',
                    'method': 'animate',
                    'args': [None, {'frame': {'duration': 0, 'redraw': True}, 'fromcurrent': True, 'transition': {'duration': 0}}]
                },
                {
                    'label': 'Stop',
                    'method': 'animate',
                    'args': [[None], {'frame': {'duration': 0, 'redraw': True}, 'mode': 'immediate', 'fromcurrent': True}]
                }
            ]
        }]
        
        # Update the figure layout
        fig.update_layout(sliders=sliders, updatemenus=updatemenus)
        
        return fig
        
    def _getOneFrameForOpacities(self, x, y, z, rangeVar0To1Row):
        colours = ['rgba({}, {:.3f})'.format(self._markerColour, opacity) for opacity in rangeVar0To1Row]
        return [go.Scatter3d(
                    x=x, y=y, z=z,
                    mode='markers',
                    marker=dict(size=self._markerSize, color=colours),
                    hovertemplate=(
                        'x (μm): %{x}<br>'
                        'y (μm): %{y}<br>'
                        'z (μm): %{z}<extra></extra>'
                    )
                )]
        
        
    def _initForColours(self, x, y, z, rangeVar, t, varNameWithIndexAndUnits, rangeVar_min, rangeVar_max):
        
        numSegms = len(x)
        numFrames = len(t)
        
        # !! here we perform the inverse operation to the one done in RangeVarAnimationPlayer.play - not optimal
        rangeVar = np.reshape(rangeVar, (numFrames * numSegms))
        
        data = {
            'x (μm)': np.concatenate([x] * numFrames),
            'y (μm)': np.concatenate([y] * numFrames),
            'z (μm)': np.concatenate([z] * numFrames),
            varNameWithIndexAndUnits: rangeVar,
            't (ms)': np.repeat(t, numSegms)
        }
        df = pd.DataFrame(data)
        
        # Create a 3D scatter plot with Plotly
        fig = px.scatter_3d(df, x='x (μm)', y='y (μm)', z='z (μm)', color=varNameWithIndexAndUnits, animation_frame='t (ms)', color_continuous_scale=self._palette, opacity=self._opacity)
        
        # Update the marker size
        fig.update_traces(marker=dict(size=self._markerSize))
        
        # Customize the colour bar
        fig.update_coloraxes(cmin=rangeVar_min, cmax=rangeVar_max, colorbar_title=varNameWithIndexAndUnits)
        
        # Maximize the animation speed
        arg = fig.layout.updatemenus[0].buttons[0].args[1]
        arg['frame']['duration'] = 0
        arg['transition']['duration'] = 0
        
        return fig
        