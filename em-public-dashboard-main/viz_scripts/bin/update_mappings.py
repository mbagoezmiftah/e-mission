# In a docker setup, run as
# sudo run_from_host/update_mappings.sh
#
#
import nbclient
import nbformat
import argparse

parser = argparse.ArgumentParser(prog="update_mappings")
parser.add_argument("mapping_notebook", help="the notebook the stores the mappings")

args = parser.parse_args()

with open(args.mapping_notebook) as f:
    nb = nbformat.read(f, as_version=4)
    nbclient.execute(nb)
