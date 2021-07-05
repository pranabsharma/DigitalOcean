#!/usr/bin/python
#This script uploads a file in DigitalOcean spaces

#*******************Prerequisites for this script**********************
#Please install the following in your Ubuntu server to run this script
#apt install python3-pip
#pip3 install boto3
#Author: Pranab Sharma (pranabksharma@gmail.com)
#**********************************************************************

import sys
import os
import socket
import json
import logging
from datetime import datetime,date,timedelta
import time
import smtplib
from boto3 import session
from botocore.client import Config

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from importlib import reload

reload(sys)  


start_time = time.time()

if len (sys.argv) != 2 :
    print ("Usage: python3 spaceUpload.py file_name")
    sys.exit (1)

file_to_upload = sys.argv[1]

#***********************Email Sending Function**********************************
def send_email(recipients,message,subject):
    msg = MIMEMultipart()
    msg['From'] = 'yourEmailID@gmail.com'
    msg['To'] = recipients
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))

    try:
        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('yourEmailID@gmail.com', 'yourPassword')

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

logFile = logDir + '/spaceUpload' + datetime.now().strftime ("%Y%m%d") + '.log'
# create a file handler
handler = logging.FileHandler(logFile)
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)
#*********************************Logging configured*************************************



#*********************Check if the setting file exists and read***********************************
settings_file = os.path.dirname(os.path.realpath(__file__)) + '/settings.json'
if not os.path.exists(settings_file):
    logger.error('Cannot find the settings file')
    sys.exit(1)

with open(settings_file) as data_file:
    try:
        data = json.load(data_file)
    except:
        logger.error('Cannot parse and load settings from the settings file')
        sys.exit(2)
#*************************Settings file check and reading done*************************************


email_recipients = ''
email_alert_line = ''
hostname = socket.gethostname()

#Create a string of email IDs for sending alerts
for email in data["emails"]:
    if email_recipients == '':
        email_recipients = email
    else:
        email_recipients = email_recipients + ',' + email


filepath, filename = os.path.split(file_to_upload)
upload_path = data["upload_path"] + '/' + hostname + '/' + filename

    # Initiate session
session = session.Session()
client = session.client('s3',
                        region_name=data["region_name"],
                        endpoint_url=data["endpoint_url"],
                        aws_access_key_id=data["access_id"],
                        aws_secret_access_key=data["secret_key"])

logger.info("Checking if file " + file_to_upload + " is already uploaded")
try:        
    resp = client.head_object(Bucket=data["spaces_name"],  Key=upload_path)    
    if resp["ResponseMetadata"]["HTTPStatusCode"] == 200:
        logger.info("File already uploaded")
    
    sys.exit(200)
except Exception as e:
    logger.error(e)    
    



logger.info("Starting file upload of " + file_to_upload)
try:
    # Upload a file to your Space    
    client.upload_file(file_to_upload, data["spaces_name"], upload_path)    
    logger.info("File uploading completed")
    
except Exception as e:
    logger.error(e)
    email_alert_line = str(e) + ' , Error in uploading File: ' + filename
    email_subject = 'Problem!!! ' + hostname + ' file ' + file_to_upload + ' uploading issue'
    sys.exit(3)


try:
        
    resp = client.head_object(Bucket=data["spaces_name"],  Key=upload_path)
    
    if resp["ResponseMetadata"]["HTTPStatusCode"] == 200:
        logger.info("File successfully uploaded")
    email_alert_line = 'File ' + filename + ' has been uploaded in space ' +  data["spaces_name"] + ' on path ' + upload_path
    email_subject = hostname + ' file ' + file_to_upload + ' uploaded in DO space'
    
except Exception as e:
    logger.error(e)
    sys.exit(4)



if email_alert_line != '':        
    #Send Email for disk space problem
    if email_recipients != '':        
        if send_email(email_recipients, email_alert_line, email_subject):
            logger.info(email_alert_line + ", Email Sent")
        else:
            logger.error(email_alert_line + ", Email Failed")


end_time = time.time()
responce_time = end_time - start_time
logger.info("Script running time is: " +  str(responce_time) + " Seconds") 
logger.info("*******************Script done*************************")

sys.exit(0)

#****************************************************************************************
