#!/usr/bin/env python
import pymongo
from subprocess import Popen, PIPE
from shlex import split
from datetime import datetime, timedelta
from urllib import quote


def run_command_no_split(command):
    sp = Popen(split(command), stdout=PIPE)
    return sp.communicate()[0].strip()


# Generate the number of CPUs
# -> Third line contains "A/I/O/T", want "T"
cpus_command = "sinfo -h -M <cluster> -p <partitions> -o '%C' -t alloc,idle,mix"

# Connect to the MongoDB at mlab
uri = "<URI>"
client = pymongo.MongoClient(uri)
db = client.get_default_database()

# Get the time, rounded down to the nearest 15 minutes
time = datetime.now()
time = time - timedelta(
    minutes=time.minute % 15, seconds=time.second, microseconds=time.microsecond
)
time_string = time.strftime("%m/%d/%y-%H:%M")

# Get [Allocated, Idle, O, Total] and convert to ints
cpu_states = [
    int(x) for x in run_command_no_split(cpus_command).split("\n")[-1].split("/")
]

# Write initial data
# print({'cluster': 'mpi', 'allocated': cpu_states[0], 'total': cpu_states[3], 'time': time_string})
db["status"].insert_one(
    {
        "cluster": "smp",
        "allocated": cpu_states[0],
        "total": cpu_states[3],
        "time": time_string,
    }
)
