#!/usr/bin/env python
import pymongo
from subprocess import Popen, PIPE
from shlex import split
from datetime import datetime, timedelta
from urllib import quote


def run_command_no_split(command):
    sp = Popen(split(command), stdout=PIPE)
    return sp.communicate()[0].strip().split('\n')[1:]


# Generate the number of GPUs
# -> Third line contains "A/I/O/T", want "T"
total_command = "sinfo -h -N -M <cluster> -p <partitions> -O gres -t alloc,idle,mix"
allocated_command = "squeue -h -M <cluster> -t RUNNING -o %b"

# Connect to the MongoDB at mlab
uri = "<URI>"
client = pymongo.MongoClient(uri)
db = client.get_default_database()

# Get the time, rounded down to the nearest 15 minutes
time = datetime.now()
time = time - timedelta(minutes=time.minute % 15,
                        seconds=time.second,
                        microseconds=time.microsecond)
time_string = time.strftime('%m/%d/%y-%H:%M')

total = sum([int(x.split(':')[-1]) for x in run_command_no_split(total_command)])
allocated = sum([int(x.split(':')[-1]) for x in run_command_no_split(allocated_command)])

# Write initial data
#print({'cluster': 'mpi', 'allocated': allocated, 'total': total, 'time': time_string})
db['status'].insert_one({'cluster': 'gpu', 'allocated': allocated, 'total': total, 'time': time_string})
