#!/usr/bin/python

#*******************Prerequisites for this script**********************
#Please install the following in your Ubuntu server to run this script
#apt install libcurl4-gnutls-dev librtmp-dev
#apt install python3-pip
#pip3 install pycurl
# Author: Pranab Sharma (pranabksharma@gmail.com)
#**********************************************************************


import sys
import pycurl
import json
import logging
import os
from io import BytesIO
from datetime import datetime,date,timedelta
from urllib.parse import urlencode
import subprocess
import time
import socket
import argparse

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from importlib import reload

from io import StringIO 

reload(sys)  



parser = argparse.ArgumentParser()
parser.add_argument("--startServices", help="Starts the dependent services after snapshot is taken", action="store_true")
parser.add_argument("--dontStopServices", help="By default script stops dependent services, this option keeps the services running while snapshot being taken for a volume", action="store_true")

args = parser.parse_args()




start_time = time.time()


#Functions for managing Linux Systemd services
#*****************************************************************************
#This function checks whether a service is running or not
def is_service_running(service_name):
    cmd = '/bin/systemctl status ' + service_name
    proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE)
    stdout_list = proc.communicate()[0].decode('utf8').split('\n')
    
    for line in stdout_list:
        if 'Active:' in line:
            if '(running)' in line:
                return True
    return False

#This function starts a service
def start_service(service_name):
    cmd = '/bin/systemctl start ' + service_name
    proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE)
    proc.communicate()
    
#This function stops a service
def stop_service(service_name):
    cmd = '/bin/systemctl stop ' + service_name
    proc = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE)
    proc.communicate()
#*******************************************************************************    


#***********************Email Sending Function**********************************
def send_email(recipients,message,subject):
    msg = MIMEMultipart()
    msg['From'] = 'emaalerts@mkcl.org'
    msg['To'] = recipients
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))

    try:
        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('emaalerts@mkcl.org', 'eM@email!7')

        try:
            mailserver.sendmail(msg['From'],recipients.split(','),msg.as_string())
            return True
        finally:
            mailserver.quit()        
    except Exception as e:
        #print e
        return False

#************************End of Email Sending*************************


#***********************************Configure Logging***********************************
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logDir = os.path.dirname(os.path.realpath(__file__)) + '/logs'
# create log directory if not already exists
if not os.path.exists(logDir):
    os.makedirs(logDir)

logFile = logDir + '/snapshot' + datetime.now().strftime ("%Y%m%d") + '.log'
# create a file handler
handler = logging.FileHandler(logFile)
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)
#*********************************Logging configured*************************************


logger.info("*******************Starting the Script*************************")


#*********************Check if the setting file exists and read***********************************
settings_file = os.path.dirname(os.path.realpath(__file__)) + '/snapshotsSettings.json'
if not os.path.exists(settings_file):
    logger.error('Cannot find the settings file')
    sys.exit(1)

with open(settings_file) as data_file:
    try:
        settings_data = json.load(data_file)
    except:
        logger.error('Cannot parse and load settings from the settings file')
        sys.exit(2)
#*************************Settings file check and reading done*************************************

region = settings_data['region']

email_recipients = ''
email_alert_line = ''
hostname = socket.gethostname()

#Create a string of email IDs for sending alerts
for email in settings_data["emails"]:
    if email_recipients == '':
        email_recipients = email
    else:
        email_recipients = email_recipients + ',' + email

#First we will stop the common services for all the volumes
if args.dontStopServices:
    email_alert_line = email_alert_line +  "Not stopping the common services as dontStopServices argument is passed<br>"
    logger.info("Not stopping the common services as dontStopServices argument is passed")
else:
    email_alert_line = email_alert_line + "Stopping all the common services which may be accessing the volume" + "<br>"
    logger.info("Stopping all the common services which may be accessing the volume")
    for service in settings_data["common_services"]:
        if is_service_running(service):
            email_alert_line = email_alert_line + "Service " + service + " is running, trying to stop it..." + "<br>"
            logger.info("Service " + service + " is running, trying to stop it...")
            count = 0
            while count < 3:
                count = count + 1
                stop_service(service)
                time.sleep(3)
                if is_service_running(service):
                    continue;
                else:
                    count = 0
                    email_alert_line = email_alert_line +  "Service " + service + " is stopped" + "<br>"
                    logger.info("Service " + service + " is stopped")
                    break;
            if count == 3:
                email_alert_line = email_alert_line + "Unable to stop service " + service + " in 3 attempt, so quiting" + "<br>"
                logger.error("Unable to stop service " + service + " in 3 attempt, so quiting")
                email_subject =  'Problem ' + hostname + ' DO Snapshot!!! ' + ' alert'
                if email_recipients != '':        
                    if send_email(email_recipients, email_alert_line, email_subject):
                        logger.info("Email Sent to :" + email_recipients)
                    else:
                        logger.error("Failed to send Email")
                sys.exit(10)
            
        else:
            email_alert_line = email_alert_line +  "Service " + service + " is NOT running" + "<br>"
            logger.info("Service " + service + " is NOT running")
    

#We will go through all the configured volumes one by one
for volume in settings_data["volumes"]:
    if args.dontStopServices:
        email_alert_line = email_alert_line +  "Not stopping the services as dontStopServices argument is passed<br>"
        logger.info("Not stopping the services as dontStopServices argument is passed")
    else:
        email_alert_line = email_alert_line + "Stopping all the services which may be accessing the volume" + "<br>"
        logger.info("Stopping all the services which may be accessing the volume")
        for service in volume["services"]:
            if is_service_running(service):
                email_alert_line = email_alert_line + "Service " + service + " is running, trying to stop it..." + "<br>"
                logger.info("Service " + service + " is running, trying to stop it...")
                count = 0
                while count < 3:
                    count = count + 1
                    stop_service(service)
                    time.sleep(3)
                    if is_service_running(service):
                        continue;
                    else:
                        count = 0
                        email_alert_line = email_alert_line +  "Service " + service + " is stopped" + "<br>"
                        logger.info("Service " + service + " is stopped")
                        break;
                if count == 3:
                    email_alert_line = email_alert_line + "Unable to stop service " + service + " in 3 attempt, so quiting" + "<br>"
                    logger.error("Unable to stop service " + service + " in 3 attempt, so quiting")
                    email_subject =  'Problem ' + hostname + ' DO Snapshot!!! ' + ' alert'
                    if email_recipients != '':        
                        if send_email(email_recipients, email_alert_line, email_subject):
                            logger.info("Email Sent to :" + email_recipients)
                        else:
                            logger.error("Failed to send Email")
                    sys.exit(10)
                
            else:
                email_alert_line = email_alert_line +  "Service " + service + " is NOT running" + "<br>"
                logger.info("Service " + service + " is NOT running")
    
    
    #Print volume information
    vol_name = volume['vol_name']
    max_total_snapshots = volume['total_snapshots']
    http_auth_header = "Authorization: Bearer " + settings_data['secret_key']
    
    email_alert_line = email_alert_line + "Finding ID of the volume: " + vol_name + "<br>"
    logger.info("Finding ID of the volume: " + vol_name)

    do_url = "https://api.digitalocean.com/v2/volumes?name=" + vol_name + "&region=" + region
    c = pycurl.Curl()
    data = BytesIO()
    c.setopt(pycurl.URL, do_url)
    c.setopt(pycurl.HTTPHEADER, [http_auth_header,'Accept: application/json'])
    c.setopt(c.WRITEFUNCTION, data.write)
    c.perform()
    dictionary = json.loads(data.getvalue())
    vol_id=dictionary['volumes'][0]['id']
    email_alert_line = email_alert_line +  "Id of the volume " + vol_name + " is : " + vol_id + "<br>"
    logger.info("Id of the volume " + vol_name + " is : " + vol_id)
    
    
    
    
    #Starting snapshot now
    
    email_alert_line = email_alert_line +  "Taking snapshot of the volume: " + vol_id + "<br>"
    logger.info("Taking snapshot of the volume: " + vol_id)
    i = datetime.now()
    cur_time = i.strftime('%Y-%m-%d-%H-%M-%S')
    snapshot_name = vol_name + '-' + cur_time
    email_alert_line = email_alert_line +  "Snapshot name is: " + snapshot_name + "<br>"
    logger.info("Snapshot name is: " + snapshot_name)
    do_url = "https://api.digitalocean.com/v2/volumes/" + vol_id + "/snapshots" 
    
    body_as_dict = {"name" : snapshot_name}
    body_as_json_string = json.dumps(body_as_dict) 
    body_as_file_object = StringIO(body_as_json_string)
    c = pycurl.Curl()
    data = BytesIO()
    c.setopt(pycurl.URL, do_url)
    c.setopt(pycurl.HTTPHEADER, [http_auth_header,'Accept: application/json'])
    
    c.setopt(pycurl.POST, 1)

    c.setopt(pycurl.READDATA, body_as_file_object) 
    c.setopt(pycurl.POSTFIELDSIZE, len(body_as_json_string))

    
    c.setopt(c.WRITEFUNCTION, data.write)
    c.perform()
    dictionary = json.loads(data.getvalue())
    #print(dictionary)
    create_status = c.getinfo(pycurl.RESPONSE_CODE)
    
    if create_status == 201:
        email_alert_line = email_alert_line + "Snapshot with name " + snapshot_name + " for volume " + vol_name + ", created with ID: " + dictionary['snapshot']['id'] + "<br>"
        logger.info("Snapshot with name " + snapshot_name + " for volume " + vol_name + ", created with ID: " + dictionary['snapshot']['id'])
    else:
        email_alert_line = email_alert_line + "Problem in creating snapshot " + snapshot_name + " for volume " + vol_name + ", got HTTP status: " + str(create_status) + "<br>"
        logger.error("Problem in creating snapshot " + snapshot_name + " for volume " + vol_name + ", got HTTP status: " + str(create_status))
    
    
    #Get Snapshots for the volume
    email_alert_line = email_alert_line +  "Finding previous snapshots of the volume: " + vol_name + "<br>"
    logger.info("Finding previous snapshots of the volume: " + vol_name)
    
    do_url = "https://api.digitalocean.com/v2/volumes/" + vol_id + "/snapshots "
    
    c = pycurl.Curl()
    data = BytesIO()
    c.setopt(pycurl.URL, do_url)
    c.setopt(pycurl.HTTPHEADER, [http_auth_header,'Accept: application/json'])
    c.setopt(c.WRITEFUNCTION, data.write)
    c.perform()
    dictionary = json.loads(data.getvalue())
    
    total_snapshots=dictionary['meta']['total']
    
    email_alert_line = email_alert_line +  "Total snapshots available for the volume " + vol_name + " is : " + str(total_snapshots) + "<br>"
    logger.info("Total snapshots available for the volume " + vol_name + " is : " + str(total_snapshots))
    
    #If we have previous snapshots for this volume, find the oldest snapshot
    if total_snapshots != 0:
        newlist = sorted(dictionary['snapshots'], key=lambda k: k['created_at'])
    
        email_alert_line = email_alert_line +  "Oldest snapshot is: " + newlist[0]['name'] + "  with ID: " + newlist[0]['id'] + "<br>"
        logger.info("Oldest snapshot is: " + newlist[0]['name'] + "  with ID: " + newlist[0]['id'])
    
        
    
    #Check if we already have the more than the number of snapshots needed
    
    if total_snapshots > max_total_snapshots :
        email_alert_line = email_alert_line +  "Total number of snapshots is now " + str(total_snapshots) + ", which is more than the configured max settings " + str(max_total_snapshots) + "<br>"
        logger.info("Total number of snapshots is now " + str(total_snapshots) + ", which is more than the configured max settings " + str(max_total_snapshots))
        email_alert_line = email_alert_line +  "Deleting snapshot with name: " + newlist[0]['name'] + ", and with ID: " + newlist[0]['id'] + "<br>"
        logger.info("Deleting snapshot with name: " + newlist[0]['name'] + ", and with ID: " + newlist[0]['id'])
        
        do_url = "https://api.digitalocean.com/v2/snapshots/" + newlist[0]['id']
    
        c = pycurl.Curl()
        data = BytesIO()
        c.setopt(pycurl.URL, do_url)
        c.setopt(pycurl.HTTPHEADER, [http_auth_header,'Accept: application/json'])
        c.setopt(pycurl.CUSTOMREQUEST, "DELETE")
        c.setopt(c.WRITEFUNCTION, data.write)
        c.perform()
        #dictionary = json.loads(data.getvalue())
        #print dictionary
        delete_status = c.getinfo(pycurl.RESPONSE_CODE)
        #print str(delete_status)
        if delete_status == 204:
            email_alert_line = email_alert_line +  "Delete request for " + newlist[0]['name'] + ", and with ID: " + newlist[0]['id'] + " is successful" + "<br>"
            logger.info("Delete request for " + newlist[0]['name'] + ", and with ID: " + newlist[0]['id'] + " is successful")
        else:
            email_alert_line = email_alert_line + "Delete request for " + newlist[0]['name'] + " failed, got HTTP response " + str(delete_status) + "<br>"
            logger.error("Delete request for " + newlist[0]['name'] + " failed, got HTTP response " + str(delete_status)) 
    else:
        email_alert_line = email_alert_line +  "Snapshot deletion not required, total number of snapshots is now " + str(total_snapshots) + ", which is within the configured max settings " + str(max_total_snapshots) + "<br>"
        logger.info("Snapshot deletion not required, total number of snapshots is now " + str(total_snapshots) + ", which is within the configured max settings " + str(max_total_snapshots))
        


    #Starting all the services which were stopped previously
    if args.startServices:
        logger.info("Starting all the services which were stopped previously")
        for service in volume['services']:
            if is_service_running(service):
                email_alert_line = email_alert_line +   "Service " + service + " is running" + "<br>"
                logger.info("Service " + service + " is running")
            else:
                email_alert_line = email_alert_line +  "Service " + service + " is NOT running, trying to start it..." + "<br>"
                logger.info("Service " + service + " is NOT running, trying to start it...")
                count = 0
                while count < 3:
                    count = count + 1
                    start_service(service)
                    time.sleep(3)
                    if is_service_running(service):
                        email_alert_line = email_alert_line +  "Service " + service + " has been started" + "<br>"
                        logger.info("Service " + service + " has been started")
                        count = 0
                        break
                    else:
                        continue
                if count == 3:
                    email_alert_line = email_alert_line +  "Unable to start service " + service + " in 3 attempt" + "<br>"
                    logger.info("Unable to start service " + service + " in 3 attempt")
    else:
        email_alert_line = email_alert_line +  "Not starting the services as startServices argument is not passed<br>"
        logger.info("Not starting the services as startServices argument is not passed")
    
    email_alert_line = email_alert_line +  "__________________Snapshot for " + vol_name + " is done______________________<br>"
    logger.info("__________________Snapshot for " + vol_name + " is done______________________")
    


#Starting all common services which were stopped previously
if args.startServices:
    logger.info("Starting all the common services which were stopped previously")
    for service in settings_data["common_services"]:
        if is_service_running(service):
            email_alert_line = email_alert_line +   "Service " + service + " is running" + "<br>"
            logger.info("Service " + service + " is running")
        else:
            email_alert_line = email_alert_line +  "Service " + service + " is NOT running, trying to start it..." + "<br>"
            logger.info("Service " + service + " is NOT running, trying to start it...")
            count = 0
            while count < 3:
                count = count + 1
                start_service(service)
                time.sleep(3)
                if is_service_running(service):
                    email_alert_line = email_alert_line +  "Service " + service + " has been started" + "<br>"
                    logger.info("Service " + service + " has been started")
                    count = 0
                    break
                else:
                    continue
            if count == 3:
                email_alert_line = email_alert_line +  "Unable to start service " + service + " in 3 attempt" + "<br>"
                logger.info("Unable to start service " + service + " in 3 attempt")
else:
    email_alert_line = email_alert_line +  "Not starting the services as startServices argument is not passed<br>"
    logger.info("Not starting the services as startServices argument is not passed")



email_subject =  hostname + ' DO Snapshot!!! ' + ' alert'
if email_alert_line != '':        
    #Send Email for snapshot
    if email_recipients != '':        
        if send_email(email_recipients, email_alert_line, email_subject):
            logger.info("Email Sent to: " + email_recipients)
        else:
            logger.error("Failed to send Email")


end_time = time.time()
responce_time = end_time - start_time
logger.info("Script running time is: " +  str(responce_time) + " Seconds") 
logger.info("*******************Script done*************************")

sys.exit(0)

#****************************************************************************************                
