#!/bin/sh
PORT=/dev/ttyS3
ID=/root/station
station=`cat $ID`

#############
if [ $station == 'Wx7' ]  ; then HOST=192.168.0.20 ; PORT=8082 ; fi
if [ $station == 'Wx8' ]  ; then HOST=192.168.0.20 ; PORT=8082 ; fi
if [ $station == 'Wx11' ] ; then HOST=192.168.0.22 ; PORT=8084 ; fi
if [ $station == 'Wx14' ] ; then HOST=192.168.0.20 ; PORT=8082 ; fi

wget http://$HOST:$PORT/oneshotimage.jpg -O image.jpg 
