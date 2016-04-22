#!/bin/bash

subsystems='cpu,cpuset,cpuacct,memory'
cgroup= $1
cgdelete $subsystems:$1
