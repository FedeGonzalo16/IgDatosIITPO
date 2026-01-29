from pymongo import MongoClient

uri = ""
client = MongoClient(uri)

#Procesos
print(client.admin.command('ping'))
###

client.close()