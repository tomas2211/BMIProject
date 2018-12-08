#-*- coding: utf-8 -*-

import numpy as np
import serial
import time
from pynput.keyboard import Key, Controller

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons

from threading import Thread
from Tkinter import *

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
        return self.ar[self.len-self.avlen:].mean()
    
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
thrsh = Scale(master, from_=0, to=1000,resolution = 0, length = 1000, orient=HORIZONTAL, label='Threshold')
thrsh.set(500)
thrsh.pack()

timout = Scale(master, from_=0, to=5000,resolution = 1, length = 1000, orient=HORIZONTAL, label='Timeout')
timout.set(200)
timout.pack()

avlen = Scale(master, from_=0, to=500,resolution = 1, length = 1000, orient=HORIZONTAL, label='Average window len')
avlen.set(200)
avlen.pack()

keyboard = Controller()

run = True
def serial_runner():
    t = time.time()
    lastprint = time.time()
    lasttrig = time.time()
    with serial.Serial('/dev/ttyUSB0',115200, timeout=1) as ser:
        print(ser.name)
        while run:
            l = ser.readline().strip()
            nt = time.time()

            dt = (nt-t)*1000
            t = nt

            if time.time() - lastprint > 1:
                print("l: %s, dt: %.3f ms" %(l,dt))
                lastprint = time.time()

            if l is not None:
                try:
                    num = int(l)
                    cr.put(num)
                except:
                    cr.put(0)
            else:
                break

            cr.set_an(avlen.get())

            if (time.time()-lasttrig)*1000 > timout.get():
                if cr.avg() > thrsh.get():
                    lasttrig = time.time()
                    print("TRIGGER")
                    keyboard.press(Key.space)
                    time.sleep(0.001)
                    keyboard.release(Key.space)



    cr.run = False

thrd_ser = Thread(target=serial_runner, args=())
thrd_ser.start()

thrd = Thread(target=cr.live_plotter, args=())
thrd.start()

mainloop()

cr.run = False
run = False
