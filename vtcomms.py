'''
Created on 5 Sep 2013

@author: Brian
'''

import socket
import time

'''
    ==============================================================================
    CLASS VTCOMMS
    ==============================================================================
    VTcomms handles the TCP connection to the VT logger
    The piVoT will only be connected to a single VT logger
    so the site will always be 0, and the logger address will always be 0
    There can be up to 16 VT modules connected to the logger with addresses 0-15
'''    
class VTcomms:
    myLog =  None
    sThisIP=""
    nThisPort = -1
    bIsBusy = False # Consider this as a Token for using the comms link to the VT system
    vtsocket = None
    # asterisk character - sent as part of the VT reply string
    AST_CHAR =  '*'
    # buffer for tcp comms
    BUFFER_SIZE = 1024
    # flag to indicate we have been able to connect
    bCanConnect = False
    
    nConnectionTimeout = None
    lastRecvdCount = 0
    
    def getSocket(self):
        return self.vtsocket
    '''
        getIsBusy returns whether the VTcomms is currently in use
        There can only be one connection to the VT system at a time
    '''
    def getIsBusy(self):
        return self.bIsBusy
    '''
        setIsBusy - set this true when a section of code will be communicating with the
        VT system. Make sure to set it false at the end of the communications
    '''
    def setIsBusy(self,bVal):
        self.bIsBusy =  bVal
        
    def getCanConnect(self):
        return self.bCanConnect
    
    def setConnectionTimeout(self, nVal):
        self.nConnectionTimeout = nVal
        
    '''
        getCommsIP returns the IP4 address of the VT system
    '''
    def getCommsIP(self):
        return self.sThisIP
    
    '''
        setCommsIP stores the IP address of the VT system
    '''
    def setCommsIP(self, s):
        self.sThisIP = s
    '''
        getCommsPort return the integer value of the TCP port we are using to talk to the VT system
        default value is 47471
    '''
    def getCommsPort(self):
        return self.nThisPort
    
    '''
        setCommsPort stores the value of the TCP port for the VT system
        value provided should be an integer - default is 47471
    '''
    def setCommsPort(self, n):
        self.nThisPort = n
    
    '''
        setHWClock sets the clock in the VT logger to the value in nTimeStamp
        nTimeStamp is a long integer, containing the number of seconds since 1/1/1970
    '''
    def setHWClock(self):
        PARAM_EE = 3 # RNV/WNV, the end of epoch time
        ME_CLOCK = 0 # WME, the clock time
        PARAM_CE = 1 # RNV, the epoch length
        
        
        #self.myLog.appendToLog("hardware clock now: " + repr(datetime.now()))
        ''' get the current hardware clock time '''
        sVal = self.requestResponse("RME "+str(ME_CLOCK)+"\r")
        lClock = long(sVal)
        ''' get the end of epoch time '''
        sVal = self.requestResponse("RNV "+str(PARAM_EE)+"\r")
        lEpochEnd = long(sVal)
        ''' get the epoch length '''
        sVal = self.requestResponse("RNV "+str(PARAM_CE)+"\r")
        lEpoch = long(sVal)
        ''' If the wait is short, wait till the epoch has elapsed '''
        if ((lEpochEnd - lClock) < 2):
            while ((lEpochEnd - lClock) > 0):
                time.sleep(0.1)
                sVal = self.requestResponse("RME "+str(ME_CLOCK)+"\r")
                lClock = long(sVal)
            sVal = self.requestResponse("RNV "+str(PARAM_EE)+"\r")
            lEpochEnd = long(sVal)
            
                
        ''' get the computer time as a long integer '''
        lNow = round(time.time())
        ''' calculate the next epoch time '''
        lValue = long((lNow/lEpoch)+1)*lEpoch
        ''' set the new hardware clock time '''
        if (lNow > lClock):
            ''' clock is being wound forward
                check whether we need to change the epoch end
            '''
            if not(lValue == lEpochEnd):
                s = self.sendCommand("WNV "+str(PARAM_EE)+" "+str(lValue)+"\r")
            ''' set the clock '''
        s = self.sendCommand("WME "+str(ME_CLOCK)+" "+str(lNow)+"\r")
        if (lNow < lClock):
            ''' clock is being wound back
                check whether we need to change the epoch end
            '''
            if not(lValue == lEpochEnd):
                s = self.sendCommand("WNV "+str(PARAM_EE)+" "+str(lValue)+"\r")
            
                
                
    
    '''
        openComms opens a TCP connection to the logger at IP sIP on port nPort
        The socket is saved as global variable vtsocket
        If the connection cannot be opened vtsocket will be None
    '''
    def openComms(self):
        self.closeComms()
        self.bCanConnect = False
        sIP = self.sThisIP
        nPort = self.nThisPort
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
            if not(self.nConnectionTimeout == None): s.settimeout(self.nConnectionTimeout)
            s.connect((sIP,nPort)) # remember to supply a tuple
            self.myLog.appendToLog("comms opened to: "+self.sThisIP)
            self.bCanConnect = True
            self.bIsBusy = False
        except socket.error:
            if s:
                s.close()
            s = None
        if (s == None):
            self.myLog.appendToLog("Unable to open comms to: "+self.sThisIP)
        self.vtsocket = s

    '''
        closeComms closes the socket and sets vtsocket to None
        Also resets the IsBusy flag to False
    '''
    def closeComms(self):
        if (self.vtsocket != None):
            self.vtsocket.close()
            time.sleep(2)
            self.vtsocket = None
        self.setIsBusy(False)
        self.bCanConnect = False
            
    '''
        requestResponse sends a request message via the open TCP socket (vtsocket)
        and returns the reply from the VT logger
        The reply should start with *, and this is removed
        Carriage Return is the terminator of the reply, and this is stripped
        A reply which starts with ! is an error message
    '''
    def requestResponse(self, sMessage):
        if (self.vtsocket == None):
            self.myLog.appendToLog("Comms socket is not open for request: "+sMessage)
            return ""
        self.vtsocket.send(sMessage)
        data = self.vtsocket.recv(self.BUFFER_SIZE)
        if (data[0]=='!'):
            self.myLog.appendToLog(" reply to request: "+sMessage.strip()+"  "+data)
            return ""
        try:
            data = data.replace(self.AST_CHAR, "")
            data = data.strip()
            #print ("requestResponse: "+sMessage+"   reply: "+data)
        except:
            print "no reply"
            data =""
        return data
    
    '''
        requestConfirmed keeps making the request until we get two identical replies
        returns one of the identical replies
    '''
    def requestConfirmed(self, sMessage):
        maxTries = 10
        bConfirmed =False
        sLast="-1"
        sThis=""
        iTry = 0
        while (not(bConfirmed) and (iTry < maxTries)):
            sThis = self.requestResponse(sMessage)
            if (sThis == sLast):
                bConfirmed=True
            sLast = sThis
            iTry += 1
        if (iTry >= maxTries): sThis = ""
        return sThis
    
    '''
        requestBinary sends sMessage as an ASCII request and expects a byte array in return
        nBytes is the maximum number of bytes expected to be returned
        returns the byte array received. Length will be 0 if no bytes received 
    '''
    def requestBinary(self, sMessage, nBytes):
        bytArray = bytearray(b" "*nBytes)
        self.lastRecvdCount = 0
        self.vtsocket.send(sMessage)
        nRecvd = self.vtsocket.recv_into(bytArray,nBytes,0)
        if (nRecvd == 0):
            self.myLog.appendToLog("requestBinary: "+sMessage+" - No data received")
        #else:
            #appendToLog"recvd: "+str(nRecvd)
        self.lastRecvdCount = nRecvd
        
        return bytArray
    
    def getLastRecvdCount(self):
        return self.lastRecvdCount
        
    '''
        getPacket returns the next packet of data received over the TCP connection
    '''
    def getPacket(self, lSize):
        try:
            # use no argument to return whatever is received
            data = self.vtsocket.recv(lSize)
        except:
            data = False
        return data

    '''
        VTenable send the message CCO 1
        to enable communications through the logger to the attached VTs
    '''    
    def VTenable(self):
        if (self.vtsocket == None):
            return False
        sMessage = "CCO 1\r"
        data = self.requestConfirmed(sMessage)
        #appendToLog"VTenable reply: "+data
        if (len(data) > 0):
            return False
        else:
            time.sleep(0.15)
            return True

    '''
        VTdisable send the message CCO 0
        to disable communications with the attached VTs
    '''    
    def VTdisable(self):
        if (self.vtsocket == None):
            return False
        sMessage = "CCO 0\r"
        data = self.requestConfirmed(sMessage)
        if (len(data) > 0):
            return False
        else:
            time.sleep(0.15)
            return True
    '''
        ==================================================================================
        These functions support the echo server
        Use the Full versions if you want the full reply
        Use the normal versions if you only want the reply value
        ==================================================================================
    '''
    '''
        requestResponseFull sends a request message via the open TCP socket (vtsocket)
        and returns the reply from the VT logger
        The reply should start with *, but this is NOT removed
        Carriage Return is the terminator of the reply, and this is NOT removed
        A reply which starts with ! is an error message
    '''
    def requestResponseFull(self, sMessage):
        if (self.vtsocket == None):
            return ""
        #print "request: "+sMessage
        self.vtsocket.send(sMessage)
        time.sleep(0.02)
        data = self.vtsocket.recv(self.BUFFER_SIZE)
        #print "reply: "+data
        if (data[0]=='!'):
            self.myLog.appendToLog(" reply to request: "+sMessage.strip()+"  "+data)
            return ""
        return data
    
    '''
        requestConfirmedFull keeps making the request until we get two identical replies
        returns one of the identical replies
    '''
    def requestConfirmedFull(self, sMessage):
        maxTries = 10
        bConfirmed =False
        sLast="-1"
        sThis=""
        iTry = 0
        while (not(bConfirmed) and (iTry < maxTries)):
            sThis = self.requestResponseFull(sMessage)
            if (sThis == sLast):
                bConfirmed=True
            sLast = sThis
            iTry += 1
        if (iTry >= maxTries): sThis = ""
        return sThis

    '''
        sendCommand sends a VT command to the logger - it expects no reply, but "\r" is returned
        to indicate receipt of the command
    '''
    def sendCommand(self,sMessage):
        if (self.vtsocket == None):
            self.myLog.appendToLog("Comms socket is not open for command: "+sMessage)
            return ""
        self.vtsocket.send(sMessage)
        #time.sleep(0.1)
        #data = self.vtsocket.recv(self.BUFFER_SIZE)
        return "*\r"
            
    '''
        VTforward sends a message received from one connection and forwards it to the VT system
        the reply from the VT system is returned
    ''' 
    def VTforward(self, sMessage):
        bReply =True
        if (sMessage[:3] == "BAT"):
            return self.BATforward(sMessage)
        
        SPACE_CHAR =' '
        if (SPACE_CHAR in sMessage):
            s1 = sMessage.split(SPACE_CHAR,1)
            if ("CCO" in s1): bReply = False
            if ("WNV" in s1): bReply = False
            if ("WME" in s1):
                bReply = False
            if ("VTW" in s1): bReply = False
            if ("VTA" in s1): bReply = False
            if ("VTH" in s1): bReply = False
        s = sMessage
        if not("\r" in s): s = s+"\r"
        if not(bReply):
            return self.sendCommand(s)
        else:
            return self.requestConfirmedFull(s)

    def BATforward(self, sMessage):
        sList = sMessage.split("\r")
        sReply = "*BAT\r"
        ''' first element in sList will be BAT
            next to last element will be EOB
            laast will be a null string (hopefully) '''
        for iCmd in range (1, len(sList)-2):
            if not("STREAM" in sList[iCmd]):
                sReply += self.VTforward(sList[iCmd])
                if ("CCO " in sList[iCmd]):
                    time.sleep(0.2)
        sReply += "*EOB\r"
        return sReply
        
    def __init__(self, loggingInstance):
        self.myLog = loggingInstance

        
