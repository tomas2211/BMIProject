#-*- coding: utf-8 -*-

import numpy as np
import serial
import time
from pynput.keyboard import Key, Controller

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons

from threading import Thread
from Tkinter import *

import chrometrexrush.main


# use ggplot style for more sophisticated visuals
plt.style.use('ggplot')

class cruncher:
    def __init__(self,n,an,min,max):
        self.ar = np.zeros(n)
        self.mean_ar = np.zeros(n)
        self.len = n
        self.line1 = []
        self.line2 = []
        self.run = True
        self.ymin = min
        self.ymax = max
        self.avlen = an

    def put(self,n):
        self.ar = np.concatenate((self.ar[1:self.len], [n]))
        self.mean_ar = np.concatenate((self.mean_ar[1:self.len], [self.avg()]))

    def avg(self):
        windowed = self.ar[self.len-self.avlen:]
        d = np.diff(windowed)
        res = np.sum(np.abs(d)) / self.avlen
        return res

    
    def set_an(self,an):
        if an < self.len:
            self.avlen = an

    def live_plotter(self):
        while self.run:
            if not self.line1:
                # this is the call to matplotlib that allows dynamic plotting
                plt.ion()
                fig = plt.figure(figsize=(13, 6))
                ax = fig.add_subplot(111)
                # create a variable for the line so we can later update it
                self.line1, = ax.plot(self.ar, '-', alpha=0.8)
                self.line2, = ax.plot(self.mean_ar, '-', alpha=0.8)
                # update plot label/title
                plt.ylabel('Y Label')
                plt.ylim([self.ymin, self.ymax])
                #plt.title('Title: {}'.format(identifier))
                plt.show()

            self.line1.set_ydata(self.ar)
            self.line2.set_ydata(self.mean_ar)
            plt.pause(0.02)




cr = cruncher(500,an=10,min=0, max=750)

master = Tk()
thrshpos = Scale(master, from_=0, to=1000,resolution = 0, length = 1000, orient=HORIZONTAL, label='Threshold +')
thrshpos.set(150)
thrshpos.pack()

thrshneg = Scale(master, from_=0, to=1000,resolution = 0, length = 1000, orient=HORIZONTAL, label='Threshold -')
thrshneg.set(20)
thrshneg.pack()

timout = Scale(master, from_=0, to=5000,resolution = 1, length = 1000, orient=HORIZONTAL, label='Timeout')
timout.set(300)
timout.pack()

avlen = Scale(master, from_=0, to=500,resolution = 1, length = 1000, orient=HORIZONTAL, label='Singal window len')
avlen.set(13)
avlen.pack()

keyboard = Controller()

run = True



def serial_runner():
    t = time.time()
    lastprint = time.time()
    lasttrig = time.time()
    has_relaxed = False
    with serial.Serial('/dev/ttyUSB0',115200, timeout=1) as ser:
        print(ser.name)
        while run:
            l = ser.readline().strip()
            nt = time.time()

            dt = (nt-t)*1000
            t = nt

            #if time.time() - lastprint > 1:
            #    print("l: %s, dt: %.3f ms" %(l,dt))
            #    lastprint = time.time()

            if l is not None:
                try:
                    num = int(l)
                    cr.put(num)
                except:
                    cr.put(0)
            else:
                break

            cr.set_an(avlen.get())

            avg = cr.avg()
            chrometrexrush.main.update_stress(avg/thrshpos.get())
            chrometrexrush.main.update_activated(has_relaxed)

            if (time.time()-lasttrig)*1000 > timout.get():
                if avg < thrshneg.get():
                    #print("Has relaxed.")
                    has_relaxed = True

                if has_relaxed and avg > thrshpos.get():
                        lasttrig = time.time()
                        print("TRIGGER")
                        has_relaxed = False
                        chrometrexrush.main.press_spacebar()



    cr.run = False

thrd_ser = Thread(target=serial_runner, args=())
thrd_ser.start()

thrd = Thread(target=cr.live_plotter, args=())
thrd.start()

thrdTrex = Thread(target=chrometrexrush.main.main, args=())
thrdTrex.start()

mainloop()

cr.run = False
run = False
