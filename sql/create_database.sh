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

sed "s/ALTER TABLE .* OWNER TO database_user\;//g" create.sql > fixed_create.sql

psql "$db_name" < fixed_create.sql

# psql fmp_test_bad -c '\dt' -o /dev/null &>/dev/null

# createdb $db_name


# sed "s/database_user/erm/g" ./create.sql > create_erm.sql



