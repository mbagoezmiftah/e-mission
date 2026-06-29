cd e-mission-server
source setup/activate.sh
cd ../saved-notebooks

PYTHONPATH=/usr/src/app/e-mission-server python bin/generate_plots.py $*
