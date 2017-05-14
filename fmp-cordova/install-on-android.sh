#!/bin/bash

export ANDROID_HOME='/home/erm/Android/Sdk'
export PATH=$PATH:$ANDROID_HOME/bin
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/platform-tools

cordova run android
