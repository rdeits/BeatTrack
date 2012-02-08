"""
This demo demonstrates how to draw a dynamic mpl (matplotlib) 
plot in a wxPython application.

It allows "live" plotting as well as manual zooming to specific
regions.

Both X and Y axes allow "auto" or "manual" settings. For Y, auto
mode sets the scaling of the graph to see all the data points.
For X, auto mode makes the graph "follow" the data. Set it X min
to manual 0 to always see the whole data from the beginning.

Note: press Enter in the 'manual' text box to make a new value 
affect the plot.

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Mostly rewritten by Robin Deits
"""
import os
import pprint
import random
import sys
import wx

# The recommended way to use wx with mpl is with the WXAgg
# backend. 
#
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab
from listener import Listener
import multiprocessing


class DataGen(object):
    def __init__(self):
        conn1, conn2 = multiprocessing.Pipe()
        self.conn = conn2
        self.listener = Listener(debug_connection = conn1)
        self.listener.start()
        self.bpm_to_test = [0]
        self.bpm_energies = [0]

    def __iter__(self):
        return self
        
    def next(self):
        while self.conn.poll():
            self.bpm_to_test, self.bpm_energies = self.conn.recv()
        return (self.bpm_to_test, self.bpm_energies)

class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = 'Demo: dynamic matplotlib graph'
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)
        
        self.datagen = DataGen()
        self.xdata, self.ydata = self.datagen.next()
        
        self.create_main_panel()
        print "Created main panel"
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(100)


    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)

        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
    
    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.set_title('BPM Energies', size=12)
        
        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data = self.axes.plot(
            self.xdata, self.ydata, 
            linewidth=1,
            color=(1, 1, 0),
            )[0]

    def draw_plot(self):
        """ Redraws the plot
        """
        # for ymin and ymax, find the minimal and maximal values
        # in the data set and add a mininal margin.
        # 
        ymin = round(min(self.ydata), 0) - 1
        ymax = round(max(self.ydata), 0) + 1
        xmin = round(min(self.xdata), 0) - 1
        xmax = round(max(self.xdata), 0) + 1

        self.axes.set_xbound(lower=xmin, upper=xmax)
        self.axes.set_ybound(lower=ymin, upper=ymax)
        

        self.plot_data.set_xdata(self.xdata)
        self.plot_data.set_ydata(self.ydata)
        
        self.canvas.draw()
    
    
    
    def on_redraw_timer(self, event):
        self.xdata, self.ydata = self.datagen.next()
        
        self.draw_plot()
    
    def on_exit(self, event):
        self.Destroy()
    

if __name__ == '__main__':
    app = wx.PySimpleApp()
    app.frame = GraphFrame()
    app.frame.Show()
    app.MainLoop()

