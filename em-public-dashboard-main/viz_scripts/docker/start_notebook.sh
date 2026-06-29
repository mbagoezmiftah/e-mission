#!/usr/bin/env bash
#Configure web server

echo "DB host = "${DB_HOST}

### configure the saved-notebooks directory for persistent notebooks

# Ensure that the database config is available so that we can connect to it
mkdir -p saved-notebooks/conf/storage
cp conf/storage/db.conf saved-notebooks/conf/storage/db.conf
cat saved-notebooks/conf/storage/db.conf

### Ensure that the analysis config is available so that we can use the functions from core
### instead of recreating them
mkdir -p saved-notebooks/conf/analysis
cp conf/analysis/debug.conf.json.sample saved-notebooks/conf/analysis/debug.conf.json.sample
cat saved-notebooks/conf/analysis/debug.conf.json.sample

#set Web Server host using environment variable
echo "Web host = "${WEB_SERVER_HOST}

# change python environment
pwd
source setup/activate.sh
conda env list

cd saved-notebooks

# launch the notebook server
# tail -f /dev/null
if [ -z ${CRON_MODE} ] ; then
    echo "Running notebook in docker, change host:port to localhost:47962 in the URL below"
    PYTHONPATH=/usr/src/app jupyter lab --no-browser --ip=0.0.0.0 --port=47962 --allow-root
else
    echo "Running crontab without user interaction, setting python path"
    export PYTHONPATH=/usr/src/app
    # tail -f /dev/null
    devcron ../crontab >> /var/log/cron.console.stdinout 2>&1
fi
