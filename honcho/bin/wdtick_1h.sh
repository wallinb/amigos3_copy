#!/bin/sh

# this is the toggle for long sleep, ie mode 1

echo 3 > /sys/class/gpio/wdt_ctl/data
sleep 1
echo 2 > /sys/class/gpio/wdt_ctl/data
sleep 1
echo 3 > /sys/class/gpio/wdt_ctl/data 
