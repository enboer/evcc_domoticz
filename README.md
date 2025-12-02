<H1><b>EVCC plugin for Domoticz</B></H1>

This plugin creates EVCC devices in Domoticz home automation. It gets the data from the EVCC MQTT messaging system. 

A switch is created to change the charging mode:

<img width="1208" height="284" alt="EVCC_Switches" src="https://github.com/user-attachments/assets/c111ce22-58d6-4432-be2c-a84285b42cc8" />
<br><br>
In the utility there are multiple devices for the ChargePower and values from the charging session. The ODO meter shows the cars milages value. And there are a few others, see this screenshot:<br><br>
<img width="1207" height="728" alt="EVCC_Utility" src="https://github.com/user-attachments/assets/44afcb18-d15f-48a5-b34e-5c1463835408" />
<h2>Installation</h2>
Create a EVCC directory in the domoticz/plugins directory. Download the plugin.py file and save this in the EVCC directory. Restart domoticz and add this plugin as new hardware. Fill in the MQTT serverdetails. the Vehicle ODO value can be filled in as initial value for the ODO device. Make sure you have domoticz enabled to add new devices.<br><br>

<img width="1140" height="577" alt="EVCC_Hardware" src="https://github.com/user-attachments/assets/f8781bd7-be60-4e83-b300-ba7caf6d2d2b" />

