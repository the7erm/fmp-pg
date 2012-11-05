#!/bin/sh

basename=`basename $0`

db_name=$1
db_user=$2
db_host=$3
db_port=$4

if [ -z "$db_name" ]
then
    echo "\nUsage:\n $basename <database_name> [<database_user>] [host] [port]"
    echo "User, host and port are optional.\n"
    exit;
fi

psql "$db_name" -c '\dt' -o /dev/null &>/dev/null
not_found=$?

if [ "$not_found" = 0 ]
then
    createdb "$db_name"
else
    echo "Database $db_name exists."
fi


psql "$db_name" < create.sql



