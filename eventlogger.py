'''
Created on 5 Sep 2013

@author: Graham
'''

import time
'''
    CLASS PIVTLOGGING
    Creates a class for appending error and event messages to a log text block
    The log text will be emailed to a known email address when the data is collected and sent
    from the VT units. This typically happens every 24 hours
'''
class PiVTlogging():
    bEchoToScreen = True
    sDatadir="c:\\windmill\\data\\"
    '''
    sLog is the text that will accumulate error and event messages
    '''
    sLog = ""

    '''
        appendToLog
        adds a message to the log text, but adds the current time to the message
    '''
    def appendToLog(self, sMessage):
        sLine = " %02d:%02d:%02d" % (time.localtime()[3], time.localtime()[4], time.localtime()[5])
        sLine += "    "+sMessage
        self.sLog+=sLine+"\r\n"
        if (self.bEchoToScreen):
            print sLine
    
    '''
        getLogText
        returns the current log text
    '''
    def getLogText(self):
        return self.sLog

    '''
        resetLogText
        clears the log text
    '''
    def resetLogText(self):
        with open(self.sDatadir+"lastLog.txt", "w") as myFile:
            myFile.write(self.sLog)
        myFile.close()
        self.sLog = ""
        
    def setDataDir(self,sVal):
        self.sDatadir = sVal
        
    def __init__(self, bEcho):
        self.bEchoToScreen=bEcho
        self.sLog =""
        
