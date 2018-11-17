import os
from time import sleep
from vad_record import record

try:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter
except ImportError:
    # for Python3
    from tkinter import *   ## notice lowercase 't' in tkinter here

class DirList(object):
    def __init__(self, initdir=None):
        self.top = Tk()
        self.top.geometry('500x300+500+200')
        self.cwd=StringVar(self.top)
        self.bfm = Frame(self.top)
        self.quit = Button(self.bfm, text='Quit',
            command=self.top.quit,
            activeforeground='white',
            activebackground='red')

        self.record = Button(self.bfm, text='开始录制',
            command=self.recordWav,
            activeforeground='white',
            activebackground='red')

        self.quit.pack(side=LEFT)
        self.record.pack(side=LEFT)
        self.bfm.pack()

        if initdir:
            self.cwd.set(os.curdir)
            self.dols()

    def clrdir(self, ev=None):
        self.cwd.set('')

    def setdirandgo(self, ev=None):
        self.last = self.cwd.get()
        self.dirs.config(selectbackground='red')
        check = self.dirs.get(self.dirs.curselection())
        if not check:
            check = os.curdir
        self.cwd.set(check)
        self.dols()

    #录音
    def recordWav(self,ev=None):
        filePathName = record();
        print(filePathName)

    def dols(self, ev=None):
        error = ''
        tdir = self.cwd.get()
        if not tdir:
            tdir = os.curdir

        if not os.path.exists(tdir):
            error = tdir + ': no such file'
        elif not os.path.isdir(tdir):
            error = tdir + ': not a directory'

        if error:
            self.cwd.set(error)
            self.top.update()
            sleep(2)
            if not (hasattr(self, 'last') \
                and self.last):
                    self.last = os.curdir
            self.cwd.set(self.last)
            self.dirs.config(
                selectbackground='LightSkyBlue')
            self.top.update()
            return

        self.cwd.set(
            'FETCHING DIRECTORY CONTENTS...')
        self.top.update()
        dirlist = os.listdir(tdir)
        dirlist.sort()
        os.chdir(tdir)

def main():
    d = DirList(os.curdir)
    mainloop()

if __name__ == '__main__':
    main()