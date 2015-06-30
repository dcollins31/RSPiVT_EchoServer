'''
Created on 7 Feb 2014

@author: Graham

This sets up a watchdog timer for posix systems (RPi)
provided the python wrapper: watchdogdev
has been installed. If not the watchdog will be inactive
Note: on the RPi the watchdog countdown takes aroud 10 seconds 
'''

try:
    from watchdogdev import *
except:
    pass

class PiVTwatchdog():

    wd = None
    
    ''' This tries to start the watchdog - if the required elements are not present
    then wd will remain None
    '''
    def start(self):
        bOK = True
        try:
            self.wd = watchdog("/dev/watchdog")
        except:
            self.wd = None
            bOK = False
        return bOK
    
    ''' This is the command to reset the watchdog countdown - or the keep alive
    '''
    def reset(self):
        if (self.wd != None):
            self.wd.keep_alive()
    

    ''' Call this to exit a program without a subsequent reboot '''
    def exit(self):
        if (self.wd != None):
            self.wd.magic_close()
            
    
