Python script to create snapshot of your block disk volumes in DigitalOcean.
Script functionalities:
1) Stops the services which may be accessing the disk (this is to prevent disk changes at the time of snapshot)
2) Maintain a configured number of disk snapshots in Digital Ocean, it will delete the older snapshots if number of snapshots exceeds the configured value. 
3) Send email alert after running the script
4) Keep log of the script run
5) You can configure multiple volume snapshot in the config file
6) Easy JSON config file


How to run this script:
1) In python 2.7 : python snapshots.py 
2) In python 3+ : python3 snapshotsPython3.py

You can pass command line argument 

i) --startServices : Starts the dependent services after snapshot is taken

ii) --dontStopServices : By default script stops dependent services, this option keeps the services running while snapshot being taken for a volume

Config file:
The default config file is snapshotsSettings.json file and should remain in the same directory as the python script. You can change the name of the config file by changing the file name in the line:
settings_file = os.path.dirname(os.path.realpath(__file__)) + '/snapshotsSettings.json'

Example config file:

	
	{
		"volumes":
		[
			{
	
				"vol_name": "db_volume",			
				"total_snapshots": 4,			
				"services": ["mysql"]
			
			}, 
			{
		
				"vol_name": "app_volume",
				"total_snapshots": 2,
				"services": ["nginx", "tomcat"]
			}
		],
		"common_services": ["haproxy"],
		"secret_key": "YOUR DIGITALOCEAN KEY",
		"region": "blr1",
		"emails": ["xyz@example.com", "abc@example.com"]
	}



