#-*- coding: utf-8 -*-

import numpy as np
import serial
import time

import matplotlib.pyplot as plt

from threading import Thread
from Tkinter import *

import chrometrexrush.main


# use ggplot style for more sophisticated visuals
plt.style.use('ggplot')

SAMPLES_MEM = 500
INIT_THRESH_POS = 150
INIT_THRESH_NEG = 20
INIT_TIMEOUT = 300
INIT_SAD_LEN = 13

class Plotter:
    def __init__(self,n,an,min,max):
        self.len = n # arrays for samples
        self.ar = np.zeros(n)

        self.mean_ar = np.zeros(n) # signal with SAD (sum of abs differences) from all samples
        self.avlen = an # number of past samples to do SAD of

        # plotting
        self.line1 = []
        self.line2 = []

        self.run = True # run flag for live plotting
        self.ymin = min # min and max on Y axis in plot
        self.ymax = max
        self.current_sad = None # store currently computed SAD to reduce overhead

    def put(self,n):
        # new sample
        self.current_sad = None
        self.ar = np.concatenate((self.ar[1:self.len], [n]))
        self.mean_ar = np.concatenate((self.mean_ar[1:self.len], [self.compute_sad()]))

    def compute_sad(self):
        # create SAD from last set of samples
        if self.current_sad is not None:
            return self.current_sad
        windowed = self.ar[self.len-self.avlen:]
        d = np.diff(windowed)
        self.current_sad = np.sum(np.abs(d)) / self.avlen
        return self.current_sad
    
    def set_an(self,an):
        # set SAD window length
        if 0 < an < self.len:
            self.avlen = an

    def live_plotter(self):
        # main loop - plotting
        print("[PLOTTER] Staring live plotting.")
        while self.run:
            if not self.line1: # first run
                # this is the call to matplotlib that allows dynamic plotting
                plt.ion()
                fig = plt.figure(figsize=(13, 6))
                fig.canvas.set_window_title('EMG live plot')
                ax = fig.add_subplot(111)

                self.line1, = ax.plot(self.ar, '-', alpha=0.8)
                self.line2, = ax.plot(self.mean_ar, '-', alpha=0.8)

                # update plot label/title
                plt.xlabel('Sample number')
                plt.ylabel('Singal magnitude')
                plt.ylim([self.ymin, self.ymax])
                plt.title('EMG live plot')
                plt.show()

            self.line1.set_ydata(self.ar)
            self.line2.set_ydata(self.mean_ar)
            plt.pause(0.02) # ~50FPS
        plt.close()
        print("[PLOTTER] Ending plotting")



plotter = Plotter(SAMPLES_MEM, an=INIT_SAD_LEN, min=0, max=750)

# Init control UI
master = Tk()
master.title('EMG Control')
thrshpos = Scale(master, from_=0, to=1000,resolution = 0, length = 1000, orient=HORIZONTAL, label='Threshold +')
thrshpos.set(INIT_THRESH_POS)
thrshpos.pack()

thrshneg = Scale(master, from_=0, to=1000,resolution = 0, length = 1000, orient=HORIZONTAL, label='Threshold -')
thrshneg.set(INIT_THRESH_NEG)
thrshneg.pack()

timout = Scale(master, from_=0, to=5000,resolution = 1, length = 1000, orient=HORIZONTAL, label='Timeout')
timout.set(INIT_TIMEOUT)
timout.pack()

avlen = Scale(master, from_=0, to=500,resolution = 1, length = 1000, orient=HORIZONTAL, label='Singal window len')
avlen.set(INIT_SAD_LEN)
avlen.pack()

#keyboard = Controller()

serial_run = True


def serial_runner():
    # serial reader - parse numbers from Arduino, send them to plotter, trigger spacebar
    print("[SERIAL] Starting serial reader")

    lasttrig = time.time()
    has_relaxed = False
    with serial.Serial('/dev/ttyUSB0',115200, timeout=1) as ser:
        print("[SERIAL]",ser.name)
        while serial_run:
            l = ser.readline().strip()

            if l is not None: # end if no input available
                try: # try to parse, put number into plotter
                    num = int(l)
                    plotter.put(num)
                except:
                    plotter.put(0)
            else:
                break

            plotter.set_an(avlen.get()) # set SAD len

            avg = plotter.compute_sad()

            chrometrexrush.main.update_stress(avg/thrshpos.get()) # update game feedback
            chrometrexrush.main.update_activated(has_relaxed)

            if (time.time()-lasttrig)*1000 > timout.get(): # after timeout, check thresholds
                if not has_relaxed and avg < thrshneg.get(): # negative threshold - after trigger
                    print("[SERIAL] Has relaxed.")
                    has_relaxed = True

                if has_relaxed and avg > thrshpos.get():
                        lasttrig = time.time()
                        print("[SERIAL] trigger")
                        has_relaxed = False
                        chrometrexrush.main.press_spacebar()
    print("[SERIAL] Ending reading")
    plotter.run = False # stop plotting, just to be sure


thrd_ser = Thread(target=serial_runner, args=()) # serial runner thread
thrd_ser.start()

thrd_plotter = Thread(target=plotter.live_plotter, args=()) # plotter thread
thrd_plotter.start()

thrdTrex = Thread(target=chrometrexrush.main.main, args=()) # game thread
thrdTrex.start()

mainloop() # start the Tkinter mainloop

chrometrexrush.main.end_game()
plotter.run = False
run = False
