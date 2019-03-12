#!/bin/bash

date
echo "Stacking is finished with all endpoints/services running"

export PATH=/usr/sbin:$PATH
source /opt/stack/new/devstack/openrc admin

date
sudo service devstack@n-cpu status

exit 1
