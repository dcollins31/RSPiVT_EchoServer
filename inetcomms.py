'''
Created on 5 Sep 2013

@author: Brian

    ===============================================================================
        INETCOMMS has classes for communications over the internet
        Supported features are:
            CLASS FTPLINK:
                Uploading data and video files to an FTP server
                Downloading new setup files from an FTP server
            CLASS UDPECHO
            CLASS TCPECHO
                TCPecho forwards VT requests to the attached VT system and returns replies
                UDPecho forwards UDP messages from a remote address to the VT system on port 47473
                    and forwards UDP packets from the VT system to the remote address
                They allow VT7viewer to be used to setup the VT as though it were directly connected
                The site IP and port should be set to:
                    IP address of the Python device (e.g. RPi) and port 47481
            CLASS VTmailer
                emails
                
            CLASS formPoster
                sends an html form by the POST method to a known html server, with php.
                The php page will store the form element values in a mySQL table
                
            CLASS QServer
                Responds to POST requests and returns an HTML page which shows current queue
                and occupancy values
'''

import socket
import ftplib
import time
import threading
import os
import cgi
# EMAILING
import smtplib
# multi-part forms
import itertools
import mimetools
import mimetypes
from cStringIO import StringIO
import urllib
import urllib2


import vtsetter
import watchdogUtils

# email
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email import Encoders
# html server
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


'''
    ==========================================================================================
    CLASS FTPLINK
    is used to upload and download files from the videoturnstile website
    ==========================================================================================
'''
class FTPLink():
    myLog = None
    listDropboxFiles = {}
    downloadFiles = ["sites.xml","wmManager.xml","Queue.ini","sensorCheck.xml","PiVT_readLogger.py"]
    startpath = "/home/pi/data/"
    sHost = "ftpproxy2.one.com"
    sUN = "davidleecollins.co.uk"
    sPWD = "Halibuf123"
    sRootDir = "/VT"
    ftp = None
    curDir = None # the current directory on the ftp server
    VEreply=0   # this is the list of expected VT addresses (as a binary number
    bIsRunning = True
    bNeedsReboot = False
    
    managerDoc = None
    myWatchdog = None
    
    def getNeedsReboot(self):
        return self.bNeedsReboot
    
    def getIsRunning(self):
        return self.bIsRunning
    
    
    def setVEreply(self,vereply):
        self.VEreply = int(vereply)

    def FTPopenLink(self):
        try:
            ipAddr = socket.gethostbyname(self.sHost)
            self.myLog.appendToLog("Connecting to "+self.sHost+ " at "+ipAddr)
            self.ftp = ftplib.FTP(ipAddr)
            self.ftp.login(self.sUN, self.sPWD)
            if not(self.rootDir()):
                self.ftp = None
        except:
            self.myLog.appendToLog("No internet connection")
            self.ftp=None
            
    def FTPclose(self):
        if (self.ftp != None):
            self.myLog.appendToLog("Closing FTP connection")
            try:
                self.ftp.quit()
            except:
                pass
            self.ftp = None
                
    def FTPterminate(self):
        if (self.ftp != None):
            self.ftp.close()

    def rootDir(self):
        try:
            self.ftp.cwd(self.sRootDir)
            self.curDir = self.sRootDir
            return True
        except:
            self.myLog.appendToLog("FTP command cwd("+self.sRootDir+") failed")
            return False

            
    def uploadFile(self, localSpec, specfile):
        ''' build the directory to the file spec '''
        if not(self.rootDir()):
            return False
        ''' reset the watchdog timer '''
        if (self.myWatchdog != None):
            self.myWatchdog.reset()

        sList = specfile.split('/')
        # goto the last but one element in the list
        n = len(sList)
        if (n > 1):
            i = 0
            while (i < n-1):
                sDir = sList[i]
                if ((not("." in sDir)) and (len(sDir)> 0)):
                    self.changeDir(sDir)
                i += 1
        try:
            self.myLog.appendToLog("Transferring: "+localSpec+"  to: "+specfile)
            ''' reset the watchdog timer '''
            if (self.myWatchdog != None):
                self.myWatchdog.reset()
            f = open(localSpec,"rb")
            a = "STOR " + sList[n-1]
            self.ftp.storbinary (a, f)
            ''' reset the watchdog timer '''
            if (self.myWatchdog != None):
                self.myWatchdog.reset()
            time.sleep(2)
            self.myLog.appendToLog("Transfer complete")
            f.close()
            ''' reset the watchdog timer '''
            if (self.myWatchdog != None):
                self.myWatchdog.reset()
            
            return True
        except:
            self.myLog.appendToLog("Failed to transfer "+localSpec)
            return False
            
    def downloadFile(self, filename, specfile):
        ''' build the directory to the file spec '''
        if not(self.rootDir()):
            return False
        ''' reset the watchdog timer '''
        if (self.myWatchdog != None):
            self.myWatchdog.reset()

        sList = specfile.split('/')
        # goto the last but one element in the list
        n = len(sList)
        if (n > 1):
            i = 0
            while (i < n-1):
                sDir = sList[i]
                if ((not("." in sDir)) and (len(sDir)> 0)):
                    self.changeDir(sDir)
                i += 1
        ''' does the file exist on the server '''
        sName = sList[n-1]
        sDirList = self.ftp.nlst()
        if not(sName in sDirList):
            self.myLog.appendToLog("File "+sName+" not found")
            return False      
        try:
            self.myLog.appendToLog("Downloading: "+specfile)
            f = open(filename,'wb')
            self.ftp.retrbinary('RETR '+sName,f.write)
            time.sleep(2)
            f.close()
            self.ftp.delete(sName)
            return True
        except:
            self.myLog.appendToLog("failed to download "+specfile)
            return False
        
    def addToList(self, localSpec, dropboxSpec):
        self.listDropboxFiles[localSpec] = dropboxSpec

    def changeDir(self,sDir):
        if (sDir == ""):
            return
        try:
            self.ftp.cwd(self.curDir+"/"+sDir)
        except:
            self.ftp.mkd(sDir)
            self.ftp.cwd(self.curDir+"/"+sDir)
        self.curDir+="/"+sDir
        #appendToLog"current FTP server directory: "+self.curDir


    def uploadList(self, liFiles):
        self.listDropboxFiles = liFiles
        #self.client = dropbox.client.DropboxClient(self.access_token)
        if (self.ftp == None):
            return
        self.myLog.appendToLog("uploading .wl files")
        n = len(self.listDropboxFiles)
        if (n == 0):
            return
        for localSpec in self.listDropboxFiles.keys():
            if (('.wl' in localSpec) or ('.ew7' in localSpec) or ('.txt' in localSpec)):               
                basename, extension = localSpec.split(".")
                if ((extension == "wl") or (extension == "ew7") or (extension == "txt")):
                    bDone = self.uploadFile(localSpec,self.listDropboxFiles[localSpec])
                    if (bDone):
                        ''' delete the dictionary entry '''
                        del self.listDropboxFiles[localSpec]
                        ''' delete the local file TODO if required'''
        self.myLog.appendToLog("uploading .vvd and .vvs files")
        n = len(self.listDropboxFiles)
        if (n == 0):
            return
        for localSpec in self.listDropboxFiles.keys():
            if ('.vv' in localSpec):               
                basename, extension = localSpec.split(".")
                if extension == "vvs" or extension == "vvd":
                    bDone = self.uploadFile(localSpec,self.listDropboxFiles[localSpec])
                    if (bDone):
                        ''' delete the dictionary entry '''
                        del self.listDropboxFiles[localSpec]
                        ''' delete the local file '''
                        ''' TODO '''
    def getFileList(self):
        return self.listDropboxFiles
                        
    def downloadList(self,myManager, mySites):
        ''' While we are connected try to download new setup files
            These come from /VT/customer/downloads/prefix/
            File names are:
                sites.xml
                wmManager.xml
                Queue.ini
                sensorCheck.xml
                PiVT_readLogger.py
        '''
        if (self.ftp == None):
            self.myLog.appendToLog('downloadList - No connection to FTP server')
            return
        sPrefix = mySites.getPrefix()
        sCustomer = myManager.getCustomer()
        dropboxDir ="/downloads/"+sCustomer+"/"+sPrefix+"/"
        localDir = myManager.getSetupsDir()
        self.bIsRunning = True  # because we must be running to have got here
        self.bNeedsReboot =False
        try:
            for s in self.downloadFiles:
                if (self.downloadFile(localDir+s, dropboxDir+s)):
                    if (s == "wmManager.xml"):
                        self.bIsRunning = False # restart program
                        self.bNeedReboot = True
                    if (s == "sites.xml"):
                        self.bIsRunning = False
                        self.bNeedReboot = False
                    if (s == "Queue.ini"):
                        self.bIsRunning = False
                        self.bNeedReboot = False
                    if (s == "sensorCheck.xml"):
                        self.bIsRunning = False
                        self.bNeedReboot = False
                    if (s == "PiVT_readLogger.py"):
                        self.bIsRunning = False
                        self.bNeedReboot = True
            ''' and now try to get new settings file for each of the attached VTs
            The file name will be:
            VTS_Pprefix_L0_VTx.xml  where x is the VT address
            '''
            ''' TODO - test this'''
            myVT = vtsetter.setVT()
            sBase = dropboxDir+"VTS_P"+sPrefix+"_L0_VT"
            nVE = self.VEreply # we have previously read the expected VT list (inreadBasicData)
            nVal = 256*128
            iAddr = 15
            while (nVal >= 1):
                if (nVE >= nVal):
                    ''' This address should exist - so try to download a new settings file '''
                    sFTPfile = sBase+str(iAddr)+".xml"
                    if (self.downloadFile(localDir+"newVT.xml", sFTPfile)):
                        myVT.getVTsettings(localDir+"newVT.xml")
                        self.myLog.appendToLog("New settings received for VT: "+str(iAddr))
                        myVT.sendSettingsToVT(self.myComms, iAddr)
                    nVE = nVE - nVal
                nVal = nVal / 2
                iAddr = iAddr - 1
        except:
            self.myLog.appendToLog("Error downloading files")
            
    def __init__(self, loggingInstance, wmManagerDoc, wd):
        self.myLog = loggingInstance
        self.managerDoc = wmManagerDoc
        self.myWatchdog = wd
        self.sHost = self.managerDoc.getFTPhost()
        self.sUN = self.managerDoc.getFTPuser()
        self.sPWD = self.managerDoc.getFTPpassword()
        self.sRootDir = self.managerDoc.getFTProotdir()



'''
    CLASSES UDPecho and TCPecho provide the two echo servers
    to allow VT command to be received from a PC running VT7viewer, passed on
    to the VT system, and the replies passed back
'''

class UDPecho(threading.Thread):
    sIn = None
    sClientAddr = ""
    TCP_IP = ""
    bNeeded = True

    def setClientAddr(self, sAddr):
        self.sClientAddr = sAddr

            
    def run(self):
        HOST=''
        buf = 1024
        nVTUDPport = 47473
        nClientPort = 47473
        '''
            we will 
            loop forever, restarting the socket as a listener
            so if one remote pc disconnects we will be ready for another connection
            Once a connection has been established, we loop forever receiving commands and forwarding
            them to the VT logger, and then returning the reply 
        '''
        try:
            self.sIn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sIn.bind(('',nVTUDPport))
        except:
            return
        while self.bNeeded:
            stat = self.sIn.recvfrom(buf)
            data, raddr = stat
            remaddr, remport = raddr 
            if data:
                #print ("udp packet from "+remaddr)
                #print ("Addresses: sClientAddr "+self.sClientAddr+"   TCP_IP "+self.TCP_IP)
                if (remaddr == self.sClientAddr):
                    nClientPort = remport
                    sForward = (self.TCP_IP, nVTUDPport)
                else:
                    sForward = (self.sClientAddr,nClientPort)

                #print "bytes recvd: "+str(len(data)), data
                if not(sForward == None):
                    if not(sForward[0]==''):
                        #print ("forwarding to: "+sForward[0])
                        stat = self.sIn.sendto(data,sForward)
                        #print "bytes forwarded: "+str(stat)
                    
        if not(self.sIn == None):
            self.sIn.shutdown(socket.SHUT_RDWR)
            self.sIn.close()
        self.sIn = None


    def close(self):
        self.bNeeded = False

        
    def __init__(self, sVTsystemAddr):
        threading.Thread.__init__(self)
        self.TCP_IP = sVTsystemAddr
        
        
class TCPecho(threading.Thread):
    myLog = None
    VTPort = 47481
    VTmonitor = None
    thisUDP = None
    bIsRunning = True
    mySelf = None

    VTPort = 47481
    
    def setComms(self, commsLink):
        self.VTmonitor = commsLink
        self.myLog.appendToLog("TCP echo server started on port: "+str(self.VTPort))
    
    def close(self):
        self.bIsRunning = False
        
    def run(self):
        nCommsStart = 0
        HOST=''
        '''
            we will loop forever, restarting the socket as a listener
            so if one remote pc disconnects we will be ready for another connection
            Once a connection has been established, we loop forever receiving commands and forwarding
            them to the VT logger, and then returning the reply 
        '''
        '''
            Open a udp echo server to send udp packets from the VT onto the connected host
        '''
        thisUDP = UDPecho(self.VTmonitor.getCommsIP())
        thisUDP.start()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
            s.bind((HOST, self.VTPort))
        except:
            return
        while self.bIsRunning:
            s.listen(0)
            conn, addr = s.accept()
            self.sClientAddr, remport = addr
            self.myLog.appendToLog("TCP echo server connection opened by "+self.sClientAddr)
            thisUDP.setClientAddr(self.sClientAddr)
            nCommsStart = time.time()
            '''
            create a comms link to the VT system
            '''
            if not(self.VTmonitor.getIsBusy()):
                self.VTmonitor.setIsBusy(True)
                bInUse = True
                try:
                    '''
                        Get data message from the connected host and send it to the VT
                    '''
                    while bInUse:
                        data = conn.recv(1024)
                        if data:
                            #print "recvd message: "+data
                            ''' does the message contain the stream command ?
                                if so we will forward it as a UDP message
                            '''
                            ''' now forward the rest through VTcomms '''
                            reply = self.VTmonitor.VTforward(data)
                            #print "reply from VT: "+reply
                            #print "reply bytes: "+str(len(reply)) + reply
                            
                            n = conn.send(reply)
                            #print "TCP reply length: "+str(n)
                            nCommsStart = time.time()
                        if ((time.time() - nCommsStart) > 60):
                            self.myLog.appendToLog("TCPecho timeout - releasing comms")
                            self.VTmonitor.setIsBusy(False)
                            bInUse = False
                except socket.error:
                    self.myLog.appendToLog("TCP echo error")
                    self.VTmonitor.setIsBusy(False)
                    bInUse = False
            conn.close()
            self.VTmonitor.setIsBusy(False)
        thisUDP.close()
        #s.shutdown(socket.SHUT_RDWR)
        s.close()
            #appendToLog("TCP echo comms released")

    def __init__(self, loggingInstance, commsLink):
        threading.Thread.__init__(self)
        self.myLog = loggingInstance
        self.setComms(commsLink)
                    
'''
    ======================================================================================
    CLASS QMESSENGER
    This emails a message in text
    and a list of files in attach
    to the videoturnstile technical support using gmail
    ======================================================================================
'''
class VTmailer():
    managerDoc = None

    def mail(self, to, subject, text, attach):
        gmail_user = "grahamad.collins@gmail.com"
        gmail_pwd = "willow17"
        
        msg = MIMEMultipart()
        if not(self.managerDoc == None ):
            gmail_user = self.managerDoc.getMailFrom()
            gmail_pwd = self.managerDoc.getMailPassword()

        msg['From'] = gmail_user
        msg['To'] = to
        msg['Subject'] = subject
    
        msg.attach(MIMEText(text))
        if (attach != ""):
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(open(attach,'rb').read())
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                    'attachment; filename="%s"'% os.path.basename(attach))
            msg.attach(part)
        try:
            mailServer = smtplib.SMTP("smtp.gmail.com",587)
            mailServer.ehlo()
            mailServer.starttls()
            mailServer.ehlo()
            mailServer.login(gmail_user,gmail_pwd)
            mailServer.sendmail(gmail_user,to,msg.as_string())
    
            mailServer.close()
        except:
            #print "Cannot contact mail server"
            return
            
    def __init__(self, wmManagerDoc):
        self.managerDoc = wmManagerDoc

'''
    ======================================================================================
    CLASS FORMMAILER
    builds and sends an html form by the POST method
    ======================================================================================
'''
class formMailer(object):
    ''' Destination for submitting the form '''
    sPostAddress = "http://www.davidleecollins.co.uk/POSTfile.php"

    '''Accumulate the data to be used when posting a form.'''

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, mimetype=None):
        """Add a file to be uploaded."""
        try:
            f = open(filename)
        except:
            #print "could not open file: "+filename
            return
        body = f.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        #print ("Fields:")
        #print self.form_fields
        parts = []
        part_boundary = '--' + self.boundary
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        #print "parts:"
        #print parts
        # Add the files to upload
        '''
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        '''
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        s =  '\r\n'.join(flattened)
        return s
    
    def addFieldList(self,dictFields):
        for sKey in dictFields.keys():
            self.add_field(sKey,dictFields[sKey])

    
    def addFile(self, sFileSpec):
        self.add_file("file", sFileSpec,"text/plain")


    def sendForm(self):
        # Build the request
        request = urllib2.Request(self.sPostAddress)
        request.add_header('User-agent', 'PiVoT (http://www.windmill.co.uk)')
        body = str(self)
        request.add_header('Content-type', self.get_content_type())
        request.add_header('Content-length', len(body))
        request.add_data(body)
        #print
        #print 'OUTGOING DATA:'
        #print request.get_data()
        #print
        #print 'SERVER RESPONSE:'
        try:
            s = urllib2.urlopen(request).read()
            request = None
            return True
        except:
            #print "Error sending form"
            request = None
            return False
        
class QHandler(BaseHTTPRequestHandler):
    myQlogger = None
   
    def do_GET(self):
        try:
            sVTmessage = self.myQlogger.getHTMLpage()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(sVTmessage)
            return
        except IOError:
            self.send_error(404,'File not found: %s' % self.path)
            
    def  do_POST(self):
        try:
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                query = cgi.parse_multipart(self.rfile, pdict)
            self.send_response(301)
                
            self.end_headers()
            upfilecontent = query.get('upfile')
            #print "filecontent", upfilecontent[0]
            self.wfile.write(",HTML>POST OK.<BR><BR>");
            self.wfile.write(upfilecontent[0]);
                
        except:
            pass

    def __init__(self, thisLogger):
        self.myQLogger = thisLogger
        
class Qserver(threading.Thread):
    server = None
    Qlogger = None

    def run(self):
        try:
            self.server = HTTPServer(('',80), QHandler(self.Qlogger))
            #print 'started httpserver...'
        except:
            #print 'Unable to create server'
            return
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            #print '^C received, closing down server'
            bRunning = 0
            self.server.socket.close()
            
    def stop(self):
        self.server.socket.close()

    def __init__(self,thisLogger):
        threading.Thread.__init__(self)
        self.Qlogger = thisLogger
