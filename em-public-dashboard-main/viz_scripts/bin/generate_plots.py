import nbclient
import nbformat
import nbparameterise as nbp
import argparse
import arrow
import requests
import json
import os
import sys
import asyncio
import emcommon.util as emcu
import emission.core.deployment_config as ecdc

# Configuration settings to use for all generated plots by this instance
# This could also be specified as a parser argument, if we want to generate plots for all programs from one instance
# Full list is at
# https://github.com/e-mission/op-deployment-configs/tree/main/configs
STUDY_CONFIG = os.getenv('STUDY_CONFIG', "stage-program")

parser = argparse.ArgumentParser(prog="generate_metrics")
parser.add_argument("plot_notebook", help="the notebook the generates the plot")
parser.add_argument("program", help="the program for the plot")
parser.add_argument("-d", "--date", nargs=2, type=int,
    help="the year and month for the plot. Default: all previous days and months since program start + one combined for the program as a whole")

args = parser.parse_args()

deployment_config = ecdc.get_deployment_config()

if deployment_config['intro']['program_or_study'] == 'program':
    if type(deployment_config['intro']['mode_studied']) == list:
        mode_studied = deployment_config['intro']['mode_studied'][0]
    else:
        mode_studied = deployment_config['intro']['mode_studied']
else:
    mode_studied = None

labels = deployment_config["label_options"]

if args.date is None:
    start_date = arrow.get(int(deployment_config['intro']['start_year']),
        int(deployment_config['intro']['start_month']), 1)
    end_date = arrow.get()
else:
    start_date = arrow.get()
    end_date = start_date

compute_range = list(arrow.Arrow.range('month', start_date, end_date))

print(f"Running at {arrow.get()} with args {args} for range {compute_range[0], compute_range[-1]}")

with open(args.plot_notebook) as f:
    nb = nbformat.read(f, as_version=4)

# Get a list of Parameter objects
orig_parameters = nbp.extract_parameters(nb)

# We will be recomputing values for multiple months
# So let's make a common function to invoke
def compute_for_date(month, year):
    params = nbp.parameter_values(
        orig_parameters,
        year=year,
        month=month,
        program=args.program,
        deployment_config=deployment_config,
        # TODO: The below params are all derived from deployment_config.
        # Since we are now passing the entire deployment_config, we should be able to
        # refactor the notebooks to not need these params anymore
        study_type=deployment_config['intro']['program_or_study'],
        mode_of_interest=mode_studied,
        include_test_users=deployment_config.get('metrics', {}).get('include_test_users', False),
        labels = labels,
        use_imperial = deployment_config.get('display_config', {}).get('use_imperial', True),
        sensed_algo_prefix=deployment_config.get('metrics', {}).get('sensed_algo_prefix', "cleaned"),
        bluetooth_only = deployment_config.get('tracking', {}).get('bluetooth_only', False),
        survey_info = deployment_config.get('survey_info', {}),
        )

    print(f"Running at {arrow.get()} with params {params}")

    # Make a notebook object with these definitions
    new_nb = nbp.replace_definitions(nb, params, execute=False)

    # Execute the notebook with the new parameters
    nbclient.execute(new_nb)

# Compute for every month until now
for month_year in compute_range:
    compute_for_date(month_year.month, month_year.year)

# Compute the overall metrics
compute_for_date(None, None)
