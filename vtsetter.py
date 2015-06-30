'''
Created on 5 Sep 2013

@author: Brian
'''

import xml.dom.minidom
from xml.dom import minidom


'''
    ============================================================================
    setVT reads a VTS_Pprefix_L0_VTx.xml file
    and sends the new settings to the VT at the specified address
    ============================================================================
'''        
class setVT:
    xmldoc = None
    
    def getVTsettings(self, filename):
        self.xmldoc = minidom.parse(filename)
    
    '''
        sendSettingsToVT reads the xml file specified
        tries to send these settings to the VT at address vtAddr
        over the comms link specified by myComms. myComms will be an instance of vtcomms
        This is the PUBLIC call from setVT
    '''
    def sendSettingsToVT(self, filename, myComms, vtAddr):
        if (filename != ""):
            self.getVTsettings(filename)
        if (self.xmldoc == None):
            return False
        memAddress = ""
        sAddr =str(vtAddr)
        if (myComms.Vtenable()):
            settings = self.xmldoc.getElementsByTagName('setting')
            for sett in settings:
                memAddress = ""
                newSetting = ""
                if (sett.nodeType == xml.dom.Node.ELEMENT_NODE):
                    for (name, value) in sett.attributes.items():
                        if (name == 'address'):
                            memAddress = value
                if not(memAddress == ""):
                    valueList = sett.getElementsByTagName('value')
                    newSetting =  valueList[0].data
                    if not(newSetting == ""):
                        ''' have the address and the new value - so send it '''
                        myComms.requestResponse("WTR "+sAddr+" "+memAddress+" "+newSetting+"\r")
            bRet = myComms.VTdisable()
            return True
        else:
            return False
        
    def __init__(self):
        self. xmldoc = None
        
