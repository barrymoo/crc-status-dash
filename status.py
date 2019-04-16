#!/usr/bin/python3
import pymongo
from subprocess import Popen, PIPE
from datetime import datetime
from datetime import timedelta
from shlex import split
import os


def run_command(command):
    sp = Popen(split(command), stdout=PIPE)
    return sp.communicate()[0].strip().split()


uri = os.environ["MONGO_URI"]
client = pymongo.MongoClient(uri)
db = client.get_database()

clusters = {
    "smp": "smp,high-mem",
    "gpu": "gtx1080,titanx,k40",
    "mpi": "opa,ib,opa-high-mem",
    "htc": "htc",
}

# Commands
cmd_sinfo = "sinfo -h -M {0} -p {1} --format='%C'"
cmd_gpu_total = "sinfo -h -N -M {0} -p {1} -O gres -t alloc,idle,mix,resv"
cmd_gpu_alloc = "squeue -h -M {0} -p {1} -t RUNNING -o %b"

# Get the time, rounded down to the nearest 15 minutes
time = datetime.now()
time = time - timedelta(
    minutes=time.minute % 15, seconds=time.second, microseconds=time.microsecond
)
time_string = time.strftime("%m/%d/%y-%H:%M")

to_insert = {"time": time_string}

for clus, parts in clusters.items():
    if clus == "gpu":
        total = 0
        for i in run_command(cmd_gpu_total.format(clus, parts)):
            entry = i.decode("utf-8")
            if "gpu:" in entry:
                total += int(entry.split(":")[-1])
        alloc = 0
        for i in run_command(cmd_gpu_alloc.format(clus, parts)):
            entry = i.decode("utf-8")
            if "gpu:" in entry:
                alloc += int(entry.split(":")[-1])
    else:
        to_parse = run_command(cmd_sinfo.format(clus, parts))[-1].decode("utf-8")
        alloc, idle, _, total = [int(x) for x in to_parse.split("/")]

    to_insert[clus] = {"total": total, "alloc": alloc}

# print(to_insert)
db["status"].insert_one(to_insert)
