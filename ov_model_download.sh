#!/bin/bash

source venv/bin/activate
mkdir -p models
omz_downloader --name pedestrian-detection-adas-0002 -o models
omz_downloader --name person-vehicle-bike-detection-2004 -o models

# Symlink system's DLStreamer GSTGVA here
ln -s /usr/lib/python3/dist-packages/gstgva gstgva