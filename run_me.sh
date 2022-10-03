#!/bin/bash

source /opt/intel/openvino_2022/setupvars.sh 
source /opt/intel/dlstreamer/setupvars.sh
source venv/bin/activate

#export PYTHONPATH=/usr/lib/python3/dist-packages

python3 ./12-add-and-remove-filesink.py