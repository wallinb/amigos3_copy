#! /bin/bash
AMIGOS_DIR=/media/mmcblk0/amigos
if [[ "$1" == "watchdog" ]]
then
    cd $AMIGOS_DIR && python cli.py $1 $2 &
else
    cd $AMIGOS_DIR && python cli.py $1 $2 $3
fi