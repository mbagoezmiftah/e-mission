#!/bin/bash
docker exec em-public-dashboard_notebook-server_1 /bin/bash -c "/usr/src/app/saved-notebooks/docker/update_mappings.sh $*"
