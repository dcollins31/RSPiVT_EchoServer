'''
Created on 25 Jun 2015

@author: G.Collins
'''

'''
The VTechoServer is for use on the RPi to echo incoming commands to the VT logger
and return replies to the client
It is intended to support the use of VT7viewer over a 3g link and uPnP, for remote commissioning of VT systems

'''
import inetcomms
import vtcomms
import eventlogger

def main():
    '''
    version 1.0 works with a VT logger at the default address
    '''
    myVersion = "1.0"
    sIP="192.168.1.61"
    nPort = 47471
    
    myEventLog = eventlogger.PiVTlogging(True)
    myEventLog.appendToLog("Starting echo server ver: "+myVersion)
    myComms = vtcomms.VTcomms(myEventLog)
    myComms.setCommsIP(sIP)
    myComms.setCommsPort(nPort)
    myComms.openComms()

    ''' Now start the tcp echo server so we can respond to VT7viewer requests '''
    myEchoServer = inetcomms.TCPecho(myEventLog,myComms)
    myEchoServer.start()
    
    
if __name__ == '__main__':
    main()
