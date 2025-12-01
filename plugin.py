# EVCC domoticz plugin
#
# Author: Erik Nijeboer
# 


"""
<plugin key="BasePlug" name="EVCC mqtt plugin" author="Erik Nijeboer" version="1.007" wikilink="" externallink="https://www.evcc.io/">
     <description>
        <h2>EVCC MQTT Plugin</h2><br/>
        
        <h3>by ErikNijeboer</h3>
        EVCC.io Plugin
    </description>
    <params>
        <param field="Address" label="MQTT Server address" width="300px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="300px" required="true" default="1883"/>
        <param field="Username" label="Username" width="300px"/>
        <param field="Password" label="Password" width="300px" default="" password="true"/>
        <param field="Mode1" label="Topic" width="125px" default="evcc"/>
        <param field="Mode2" label="Vehicle ODO" width="125px" default="0"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>


    </params>
</plugin>
"""
errmsg = ""
subval = ""

try:
 import Domoticz
except Exception as e:
 errmsg += "Domoticz core start error: "+str(e)
try:
 import os
except Exception as e:
 errmsg += "OS lib import error: "+str(e)
try:
 import string
except Exception as e:
 errmsg += "String lib import error: "+str(e)
try:
 import json
except Exception as e:
 errmsg += " Json import error: "+str(e)
try:
 import time
except Exception as e:
 errmsg += " time import error: "+str(e)
try:
 import re
except Exception as e:
 errmsg += " re import error: "+str(e)
try:
 from mqtt import MqttClientSH2
except Exception as e:
 errmsg += " MQTT client import error: "+str(e)
try:
 import datetime
except Exception as e:
 errmsg += " datetime import error: "+str(e)

from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request

DEVICE_MAPPING = {
    "Vehicle ODO": 1,
    "Charge Mode": 2,
    "Vehicle SOC": 3,
    "Session Solar": 4,
    "Charge Power": 5,
    "Offered Current": 6,
    "Active Phases": 7,
    "Connection": 8,
}

REVERSE_DEVICE_MAPPING = {
    1:  "Vehicle ODO",
    2:  "Charge Mode",
    3:  "Vehicle SOC",
    4:  "Session Solar",
    5:  "Charge Power",
    6:  "Offered Current",
    7:  "Active Phases",
    8:  "Connection",
}

TOPIC_MAPPING = {
    "evcc/loadpoints/1/vehicleOdometer": 1,
    "evcc/loadpoints/1/mode": 2,
    "evcc/loadpoints/1/vehicleSoc": 3,
    "evcc/loadpoints/1/sessionSolarPercentage": 4,
    "evcc/loadpoints/1/chargePower": 51,
    "evcc/loadpoints/1/sessionEnergy": 52,
    "evcc/loadpoints/1/chargeCurrents/l1": 61,
    "evcc/loadpoints/1/chargeCurrents/l2": 62,
    "evcc/loadpoints/1/chargeCurrents/l3": 63,
    "evcc/loadpoints/1/phasesActive": 7,
    "evcc/loadpoints/1/connected": 8,
}


class EVCC_MQTT:
    domoticzURL = "http://192.168.2.8:8080"
    sessionKWH = "sessionKWH"
    
    def __init__(self, ip_address: str, port: int, base_topic: str):    
        self._mqttclient = MqttClientSH2(ip_address, port, "", self.onMQTTConnected, self.onMQTTDisconnected, self.onMQTTPublish, self.onMQTTSubscribed)
        self.base_topic = base_topic
    
    def isConnected(self):
        self._mqttclient.isConnected
        
    def onMQTTConnected(self):
        Domoticz.Debug("onMQTTConnected")       
        if self._mqttclient is not None:
            self._mqttclient.subscribe([self.base_topic + '/#'])

    
    def onMQTTDisconnected(self):
        Domoticz.Debug("onMQTTDisconnected")
    
    def onMQTTSubscribed(self):
        Domoticz.Debug("onMQTTSubscribed")   

    def onMQTTPublish(self, topic, message): # process incoming MQTT statuses
        try:
            topic = str(topic)
            mval = str(message).strip()
        except:
            Domoticz.Debug("MQTT message is not a valid string!") 
            return False

        try:
            UnitID=TOPIC_MAPPING[topic]
        except KeyError:
            return False
           
        UnitID = TOPIC_MAPPING.get(topic)
        Domoticz.Log(f"MQTT message {UnitID} {topic} {mval}")
        SubIndex = 0
        if UnitID >= 10:
            UnitID = TOPIC_MAPPING.get(topic) // 10
            SubIndex = TOPIC_MAPPING.get(topic) % 10
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Debug(f"MQTT message {topic}")
        
        match UnitID:
           
            case 1:  # Vehicle ODO
                # http://192.168.2.8:8080/json.htm?type=command&param=udevice&idx=11798&svalue=0;10675
                self.read_time = time.time()
                Domoticz.Debug(f"ODO {Devices[UnitID].sValue}")
                current_ODO = int(mval)
                try:
                    old_ODO=int(Devices[UnitID].sValue.split(";")[0])
                except Exception as e:
                    Domoticz.Error(f"Cannot read value from device {DeviceName}: {str(e)}")
                    return False
                increment_km=str(current_ODO - old_ODO)
                output_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if current_ODO !=0:
                    new_svalue=f"{current_ODO}"
                    Devices[UnitID].Update(nValue=0, sValue=new_svalue) 
                    
            case 2:  # Charge Mode
                self.read_time = time.time()
                if (mval=="off"):
                    mval="0"
                elif (mval=="pv"):
                    mval="10"
                elif (mval=="minpv"):
                    mval="20"
                elif (mval=="now"):
                    mval="30"
                try:
                    Devices[UnitID].Update(1,str(mval))
                except Exception as e:
                    Domoticz.Error(f"Cannot update device {DeviceName}: {str(e)}")
                    return False           
            case 3:  # Vehicle SOC
                #Devices[2].Update(nValue=0, sValue=sFloat.replace('.',''))
                Domoticz.Debug(f"SOC {DeviceName} {UnitID} {Devices[UnitID].sValue} {mval}")
                self.read_time = time.time()
                
                newval="{:.0f}". format(float(mval))  
                try:
                    if int(newval) > 0: 
                        # newval="{:.2f}". format(float(mval))  
                        Devices[UnitID].Update(nValue=0, sValue=f"{newval}")
                        Domoticz.Debug(f"SOC {newval}")
                except Exception as e:
                    Domoticz.Error(str(e))
                    return False                    
            case 4:  # Solar Percentage
                self.read_time = time.time()
                Domoticz.Debug(f"SolarPercentage Update: {mval} {UnitID} Svalue: {Devices[UnitID].sValue}")
                try:
                    Devices[UnitID].Update(nValue=0, sValue=f"{mval}") 
                except Exception as e:
                    Domoticz.Error(str(e))
                    return False 
         
            case 5:  # Charge Power Watt and SessionKWH
                self.read_time = time.time()
                Domoticz.Debug(f"Charge Power: {Devices[UnitID].sValue}")
                if SubIndex==1: # actual Watts
                    try:
                        sessionkwh=Devices[UnitID].sValue.split(";")[1]
                        svalue=f"{mval};{sessionkwh}"
                        Domoticz.Debug(f"ChargePower svalue: {sessionkwh} Message: {mval}")                       
                    except Exception as e:
                        Domoticz.Error(f"Cannot get svalue from KWH device {mval} {sessionkwh} {str(e)}")
                        return False
                    Devices[UnitID].Update(nValue=0, sValue=f"{svalue}")
                else: # sessionKWH Update
                    currentDevicekwh=int(Devices[UnitID].sValue.split(";")[1])
                    previousKWH = int(self.getDomoticzVariable(self.sessionKWH_idx))
                    Domoticz.Debug("OldKWH: "+ str(previousKWH) + " " + str(previousKWH_File) )
                    try:
                        currentpower=Devices[UnitID].sValue.split(";")[0]
                    except:         
                        currentpower="0"                 				   
                    if previousKWH < int(mval) and int(mval) != 0:  
                        newKWH=currentDevicekwh + int(mval) - previousKWH
                        svalue=f"{currentpower};{newKWH}"  
                        Domoticz.Debug(f"ChargePower Update: {previousKWH} {mval} {UnitID} {svalue} Svalue:" + Devices[UnitID].sValue )
                        self.setDomoticzVariable(self.sessionKWH_idx, mval)  
                        Domoticz.Debug(f"IDX: {self.sessionKWH_idx}")
                        try: 
                            Devices[UnitID].Update(nValue=0, sValue=f"{svalue}")
                        except Exception as e:
                            Domoticz.Debug(str(e))
                            return False 
                    if int(mval)==0:
                        self.setDomoticzVariable(self.sessionKWH_idx, "0")
              
            case 6:   # Charge Currents 3 Phase 
                DeviceName=DEVICE_MAPPING.get(UnitID)                
                self.read_time = time.time()
                Old_Amp=Devices[UnitID].sValue.split(";")
                Len_Old_Amp=len(Old_Amp)
                if len(Old_Amp) < 3:
                    Old_Amp=["0","0","0"]
                    Len_Old_Amp=len(Old_Amp)  
                if SubIndex==1:
                    sValue=f"{mval};{Old_Amp[1]};{Old_Amp[2]};"
                elif SubIndex==2:
                    sValue=f"{Old_Amp[0]};{mval};{Old_Amp[2]};"
                elif SubIndex==3:
                    sValue=f"{Old_Amp[0]};{Old_Amp[1]};{mval};"
                  
                old_svalue=Devices[UnitID].sValue            
                Domoticz.Debug(f"OfferedCurrent Update: {mval} {UnitID} Svalue: {sValue} OldValue: {old_svalue}")
                try:
                    Devices[UnitID].Update(nValue=0, sValue=f"{sValue}") 
                except Exception as e:
                    Domoticz.Debug(str(e))
                    return False         

            case 7:   # Number of Phases 
                self.read_time = time.time()                
                Domoticz.Debug(f"Active Phases Update: {mval} {UnitID} Svalue: {Devices[UnitID].sValue}")
                try:
                    Devices[UnitID].Update(nValue=0, sValue=f"{mval};0") 
                except Exception as e:
                    Domoticz.Debug(str(e))
                    return False         
         
            case 8:    # Car Connected 
                self.read_time = time.time()                   
                Domoticz.Debug(f"Car Connected Update: {mval}  {mval.islower()} {UnitID} Svalue: {Devices[UnitID].sValue}")
                if mval.lower()=="true":
                    svalue="Car Connected"
                else: 
                    svalue="Car Disconnected"
                try:
                    Devices[UnitID].Update(nValue=0, sValue=svalue) 
                except Exception as e:
                    Domoticz.Debug(str(e))
                    return False     


        Domoticz.Debug("MQTT message: " + topic + " " + str(message))    
        
    def checkLastSeen(self):
        for UnitID in Devices:         
            Domoticz.Debug(f"Check Lastseen: {UnitID} {Devices[UnitID]}")
            lastseen = str(Devices[UnitID].LastUpdate).split(" ")
            
            date = lastseen[0].split("-")
            time = lastseen[1].split(":") 
            
            current_minutes = int(datetime.datetime.now().strftime("%M"))
            current_hour = int(datetime.datetime.now().strftime("%H"))
            Domoticz.Debug(f"LastSeen: {time[1]} {time[0]} {current_minutes} {UnitID} {lastseen}")    
            
            if (int(time[1]) < (current_minutes - 14)) or (int(time[0]) <= (current_hour - 1)):
                #UnitID = DEVICE_MAPPING.get(Device) 
                Domoticz.Debug(f"test {time[1]} {current_minutes} {UnitID}")
                old_sValue=Devices[UnitID].sValue
                old_nValue=Devices[UnitID].nValue
                Devices[UnitID].Update(nValue=old_nValue, sValue=old_sValue)
        return True        
              
    def createEVCCDevice(self):
        DevicesList = list()
  
        for Device in Devices:         
            Domoticz.Debug(f"Device: {Devices[Device]}")                      
            DeviceID = Devices[Device].DeviceID
            DevicesList.append(DeviceID)  
 
        Domoticz.Debug(f"Current Devices {DevicesList}")    
        
        # ODO (1)
        UnitID = 1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}") 
        try:
          deviceIndex = DevicesList.index(DeviceName)
          # Domoticz.Log(f"{UnitID} {DeviceName} {deviceIndex}")
        except:
          Domoticz.Error(f"{DeviceName} not Found") 
          Domoticz.Error(f"{UnitID} {DeviceName}")
          Options={ "ValueQuantity": "Trip", "ValueUnits": "KM" }
          Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=113, Switchtype=3, Options=Options, Used=1).Create()
          newSvalue=f"{self.ODOmeter}"     
          Devices[UnitID].Update(nValue=0, sValue=newSvalue) 

        # ChargeMode (2)
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}") 
        
        try:
          deviceIndex = DevicesList.index(DeviceName)
        except:
            Domoticz.Error(f"{DeviceName} not Found, creating.") 
            Options =   {   "LevelActions"  :"||||||" , 
                            "LevelNames"    :"Off|PV|Min+PV|Snel" ,
                            "LevelOffHidden":"false",
                            "SelectorStyle" :"0"
                  }		                  
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, TypeName="Selector Switch", Switchtype=18, Image=12, Options=Options, Used=1).Create()

        # Vehicle SOC (3)
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}")  
        try:
            deviceIndex = DevicesList.index(DeviceName)
        except:
            Domoticz.Error(f"{DeviceName} not Found, creating.") 
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=243, Subtype=6, Switchtype=0, Used=1).Create()   

        # Session Solar Percentage (4)
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}") 
        try:
            deviceIndex = DevicesList.index(DeviceName)
        except:
            Domoticz.Error(f"{DeviceName} not Found, creating.") 
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=243, Subtype=6, Switchtype=0, Used=1).Create()

        # Charge Power Percentage (5)
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}") 
        try:
            deviceIndex = DevicesList.index(DeviceName)
        except:        
            Domoticz.Error(f"{DeviceName} not Found") 
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=243, Subtype=29, Switchtype=1, Used=1, ).Create()
            Devices[UnitID].Update(nValue=0, sValue="0;0")
          
        # 3Phase Currents (6)
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}") 
        try:
            deviceIndex = DevicesList.index(DeviceName)
        except:
            Domoticz.Error(f"{DeviceName} not Found, creating.")  
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=89, Subtype=1, Switchtype=0, Used=1).Create()               

        # Number of Phases (7)
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}") 
        try:
            deviceIndex = DevicesList.index(DeviceName)
        except:
            Domoticz.Error(f"{DeviceName} not Found, creating.") 
            Options={ "ValueQuantity": "Phases", "ValueUnits": "Phases" }
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=243, Subtype=31, Options=Options, Used=1).Create()
        
        # Connected
        UnitID+=1
        DeviceName=REVERSE_DEVICE_MAPPING.get(UnitID)
        Domoticz.Log(f"Device: {DeviceName} {UnitID}")  
        try:
            deviceIndex = DevicesList.index(DeviceName)
        except:
            Domoticz.Error(f"{DeviceName} not Found, creating.") 
            Domoticz.Device(Name=DeviceName, DeviceID=DeviceName, Unit=UnitID, Type=243, Subtype=19, Used=1).Create()

        Domoticz.Log("End Devices")

    def sendMQTTtopic(self, Unit, Command, Level, Color):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level)+", DeviceID: "+Devices[Unit].DeviceID )
        DeviceName=Devices[Unit].DeviceID
        UnitID = DEVICE_MAPPING.get(DeviceName)
        Domoticz.Log(f"DeviceNR: {DeviceName} {UnitID}")
        cmode=""
        
        if(UnitID ==2 ):
            if (Level==0):
                cmode="off"
            elif (Level==10):
                cmode="pv"
            elif (Level==20):
                cmode="minpv"
            elif (Level==30):
                cmode="now"        
            evccTopic = self.base_topic + "/loadpoints/1/mode/set"
            Domoticz.Debug("ChargeMode: " + evccTopic + " " + cmode)
          
        if (self._mqttclient.isConnected):
            try:
                Domoticz.Debug("Publish")
                self._mqttclient.publish(evccTopic, cmode)
            except Exception as e:
                Domoticz.Error(str(e))   

    def checkDomoticzVariable(self):
        with urlopen(f"{self.domoticzURL}/json.htm?type=command&param=getuservariables") as url:
            data = json.loads(url.read().decode())
        all_vars = data["result"]      
        self.sessionKWH_idx = -1
        
        for i, item in enumerate(all_vars):
            name = item["Name"]
            if name == self.sessionKWH:
                self.sessionKWH_idx= item["idx"]
                Domoticz.Debug(f"IDX sessionKWH: {self.sessionKWH_idx}") 
                
        if self.sessionKWH_idx == -1:            
            with urlopen(f"{self.domoticzURL}/json.htm?type=command&param=adduservariable&vname={self.sessionKWH}&vtype=0&vvalue=0") as url:
                data = json.loads(url.read().decode())
                Domoticz.Debug(f"Creating Var {self.sessionKWH}")
            status = data["status"]

            if status == "OK":
                self.sessionKWH_idx = int(all_vars[-1]["idx"]) + 1
                Domoticz.Debug(f"Created: {self.sessionKWH_idx} {status}")
                return True
            else:
                Domoticz.Debug("Failed to create variable")
                return False           
        else:
            Domoticz.Debug(f"Variable {self.sessionKWH} Exist")

    def getDomoticzVariable(self, varID: int):                
        with urlopen(f"{self.domoticzURL}/json.htm?type=command&param=getuservariable&idx={varID}") as url:
            data = json.loads(url.read().decode())
        Domoticz.Debug(f"{data}")           
        VariableValue = data["result"][0]["Value"]
        Domoticz.Debug(f"Variable: {varID} {VariableValue}")
        
        return VariableValue

    def setDomoticzVariable(self, varID: int, newValue: str):
        Domoticz.Debug("SetVAriableFunction") 
        with urlopen(f"{self.domoticzURL}/json.htm?type=command&param=getuservariable&idx={varID}") as url:
            data = json.loads(url.read().decode())
        varName = data["result"][0]["Name"]
        varType = data["result"][0]["Type"]      
        Domoticz.Debug(f"{varName} {varType}")
        
        with urlopen(f"{self.domoticzURL}/json.htm?type=command&param=updateuservariable&vname={varName}&vtype={varType}&vvalue={newValue}") as url:
                    data = json.loads(url.read().decode())
        Domoticz.Debug(f"{data}")           
        status = data["status"]
        Domoticz.Debug(f"Variable: {varID} {status}")
        if status == "OK":
            return True
        else:
            return False  


class BasePlugin:
    enabled = False
    mqttConn = None
    counter = 0
    mqttClient = None
    errmsg = ""
    subval = ""
    response = ""
    plugged = "0"
    ManualOverride = "0"
    sessionKWH = -1	
    read_time = time.time()
    elapsed_time = 0
    
    def __init__(self):
        return

    def onStart(self):
        global errmsg
                
        if errmsg =="":
            try:
                Domoticz.Heartbeat(10)
                self.base_topic = Parameters["Mode1"] 
                self.ODOmeter = Parameters["Mode2"] 
            
                # self.hardwarename = Parameters["Name"].strip()
                if Parameters["Mode6"] != "0":
                    Domoticz.Debugging(int(Parameters["Mode6"]))
                    DumpConfigToLog()          
                self._client = EVCC_MQTT(ip_address=Parameters["Address"], port=Parameters["Port"], base_topic=self.base_topic)
                self._client.createEVCCDevice()
                self._client.checkDomoticzVariable()
                
            except Exception as e:
                Domoticz.Error("MQTT client start error: "+str(e))
                self._mqttclient = None
        else:
            Domoticz.Error("Your Domoticz Python environment is not functional! "+errmsg)
            self._mqttclient = None
                   
    # executed each time we click on device thru domoticz GUI
    def onCommand(self, Unit, Command, Level, Color):  #
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level)+", DeviceID: "+Devices[Unit].DeviceID )
        # Charge Mode
        self._client.sendMQTTtopic( Unit, Command, Level, Color )

          			 
    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("MQTT connected successfully.")
            sendData = { 'Verb' : 'CONNECT' }
            Connection.Send(sendData)
        else:
            Domoticz.Error("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Port"]+" with error: "+Description)

    def onMessage(self, Connection, Data):
        if self._client._mqttclient is not None:
            self._client._mqttclient.onMessage(Connection, Data)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")
        self._client._mqttclient.isConnected = False

    def onHeartbeat(self):
        Domoticz.Debug("Heartbeating...")
      
        if self._client._mqttclient is None:
            Domoticz.Error("Could not update values, because MQTT is not initialized")
            return
      
        if self._client._mqttclient is not None:
            try:
                # Reconnect if connection has dropped
                if (self._client._mqttclient._connection is None) or (not self._client._mqttclient.isConnected):
                    Domoticz.Debug("Reconnecting")
                    self._client._mqttclient._open()
                else:
                    self._client._mqttclient.ping()
            except Exception as e:
                Domoticz.Error(str(e))           
        self.elapsed_time = time.time() - self.read_time
        Domoticz.Debug(f"Lastseen: {time.time()}  {self.read_time} ")

        current_minutes = int(datetime.datetime.now().strftime("%M"))
        
        if (current_minutes % 15) == 0 or current_minutes == 59:
            Domoticz.Debug("Check LastSeen")
            result = self._client.checkLastSeen()
        
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)
def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)
def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpDictionaryToLog(theDict, Depth=""):
    if isinstance(theDict, dict):
        for x in theDict:
            if isinstance(theDict[x], dict):
                Domoticz.Log(Depth+"> Dict '"+x+"' ("+str(len(theDict[x]))+"):")
                DumpDictionaryToLog(theDict[x], Depth+"---")
            elif isinstance(theDict[x], list):
                Domoticz.Log(Depth+"> List '"+x+"' ("+str(len(theDict[x]))+"):")
                DumpListToLog(theDict[x], Depth+"---")
            elif isinstance(theDict[x], str):
                Domoticz.Log(Depth+">'" + x + "':'" + str(theDict[x]) + "'")
            else:
                Domoticz.Log(Depth+">'" + x + "': " + str(theDict[x]))

def DumpListToLog(theList, Depth):
    if isinstance(theList, list):
        for x in theList:
            if isinstance(x, dict):
                Domoticz.Log(Depth+"> Dict ("+str(len(x))+"):")
                DumpDictionaryToLog(x, Depth+"---")
            elif isinstance(x, list):
                Domoticz.Log(Depth+"> List ("+str(len(theList))+"):")
                DumpListToLog(x, Depth+"---")
            elif isinstance(x, str):
                Domoticz.Log(Depth+">'" + x + "':'" + str(theList[x]) + "'")
            else:
                Domoticz.Log(Depth+">'" + x + "': " + str(theList[x]))

    