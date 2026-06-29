import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from collections import defaultdict
from collections import OrderedDict
import difflib
import logging

import emission.storage.timeseries.abstract_timeseries as esta
import emission.storage.timeseries.tcquery as esttc
import emission.core.wrapper.localdate as ecwl
import emcommon.diary.base_modes as emcdb
import emcommon.util as emcu
import emcommon.metrics.footprint.footprint_calculations as emffc
# Module for pretty-printing outputs (e.g. head) to help users
# understand what is going on
# However, this means that this module can only be used in an ipython notebook

import IPython.display as disp

import emission.core.get_database as edb

def no_traceback_handler(exception_type, exception, traceback):
    print("%s: %s" % (exception_type.__name__, exception), file=sys.stderr)

def get_time_query(year, month):
    if year is None and month is None:
        return None

    if month is None:
        assert year is not None
        query_ld = ecwl.LocalDate({"year": year})
    else:
        assert year is not None and month is not None
        query_ld = ecwl.LocalDate({"year": year, "month": month})
    tq = esttc.TimeComponentQuery("data.start_local_dt", query_ld, query_ld)
    return tq

def get_participant_uuids(program, load_test_users):
    """
        Get the list of non-test users in the current program.
        Note that the "program" parameter is currently a NOP and should be removed in
        conjunction with modifying the notebooks.
    """
    all_users = pd.json_normalize(list(edb.get_uuid_db().find()))
    # CASE 1 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if len(all_users) == 0:
        return []
    if load_test_users:
        participant_list = all_users
    else:
        participant_list = all_users[np.logical_not(all_users.user_email.str.contains("_test_"))]
    participant_uuid_str = participant_list.uuid
    disp.display(participant_list.user_email)
    return participant_uuid_str

async def add_base_mode_footprint(trip_list, labels):
    #TODO filter ahead of this so only labeled trips get a footprint OR display uncertainties
    value_to_basemode = {mode["value"]: mode.get("base_mode", mode.get("baseMode", "UNKNOWN")) for mode in labels["MODE"]}
    
    counter_trip_error = 0
    for trip in trip_list:
        #format so emffc can get id for metadata
        trip['data']['_id'] = trip['_id']
        if trip['data']['user_input'] != {}:
            try:
                trip['data']['base_mode'] = value_to_basemode.get(trip['data']['user_input']['mode_confirm'], "UNKNOWN")
                trip['data']['mode_confirm_footprint'], trip['data']['mode_confirm_footprint_metadata'] = await emffc.calc_footprint_for_trip(trip['data'], labels, mode_key='mode')
                
                if 'replaced_mode' in trip['data']['user_input'].keys():
                    trip['data']['user_input']['replaced_mode_confirm'] = trip['data']['user_input']['replaced_mode']
                    trip['data']['replaced_base_mode'] = value_to_basemode.get(trip['data']['user_input']['replaced_mode'], "UNKNOWN")
                    trip['data']['replaced_mode_footprint'],  trip['data']['replaced_mode_footprint_metadata'] = await emffc.calc_footprint_for_trip(trip['data'], labels,  mode_key='replaced_mode')
                else:
                    trip['data']['replaced_base_mode'] = "UNKNOWN"
                    trip['data']['replaced_mode_footprint'] = {}
                    
            except Exception as e:
                counter_trip_error = counter_trip_error + 1
                logging.exception(f"Exception in add_base_mode_footprint for trip - {trip['data']['_id']}")
                trip['data']['base_mode'] = "UNKNOWN"
                trip['data']['replaced_base_mode'] = "UNKNOWN"
                trip['data']['mode_confirm_footprint'] = {}
                trip['data']['replaced_mode_footprint'] = {}
    logging.debug(f"There are {counter_trip_error} trip errors")
    return trip_list

async def load_all_confirmed_trips(tq, labels, add_footprint):
    agg = esta.TimeSeries.get_aggregate_time_series()
    result_it = agg.find_entries(["analysis/confirmed_trip"], tq)
    if add_footprint:
        processed_list = await add_base_mode_footprint(list(result_it), labels)
        all_ct = agg.to_data_df("analysis/confirmed_trip", processed_list)
    else:
        all_ct = agg.to_data_df("analysis/confirmed_trip", result_it)
    print("Loaded all confirmed trips of length %s" % len(all_ct))
    disp.display(all_ct.head())
    return all_ct

async def load_all_participant_trips(program, tq, load_test_users, labels, add_footprint=False):
    participant_list = get_participant_uuids(program, load_test_users)
    all_ct = await load_all_confirmed_trips(tq, labels, add_footprint)
    # CASE 1 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if len(all_ct) == 0:
        return all_ct
    participant_ct_df = all_ct[all_ct.user_id.isin(participant_list)]
    print("After filtering, found %s participant trips " % len(participant_ct_df))
    disp.display(participant_ct_df.head())
    return participant_ct_df

def filter_labeled_trips(mixed_trip_df):
    # CASE 1 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if len(mixed_trip_df) == 0:
        return mixed_trip_df
    labeled_ct = mixed_trip_df[mixed_trip_df.user_input != {}]
    print("After filtering, found %s labeled trips" % len(labeled_ct))
    disp.display(labeled_ct.head())
    return labeled_ct

def filter_inferred_trips(mixed_trip_df):
    # CASE 1 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if len(mixed_trip_df) == 0:
        return mixed_trip_df
    # Identify trips which has either inferred_labels or has user_input
    inferred_ct = mixed_trip_df[(mixed_trip_df['inferred_labels'].apply(lambda x: bool(x))) | (mixed_trip_df.user_input != {})]
    print("After filtering, found %s inferred trips" % len(inferred_ct))
    disp.display(inferred_ct.head())
    return inferred_ct

def expand_userinputs(labeled_ct):
    '''
    param: labeled_ct: a dataframe of confirmed trips, some of which have labels
    params: labels_per_trip: the number of labels for each trip.
        Currently, this is 2 for studies and 3 for programs, and should be 
        passed in by the notebook based on the input config.
        If used with a trip-level survey, it could be even larger.
    '''
    # CASE 1 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if len(labeled_ct) == 0:
        return labeled_ct
    label_only = pd.DataFrame(labeled_ct.user_input.to_list(), index=labeled_ct.index)
    disp.display(label_only.head())
    labels_per_trip = len(label_only.columns)
    print("Found %s columns of length %d" % (label_only.columns, labels_per_trip))
    expanded_ct = pd.concat([labeled_ct, label_only], axis=1)
    assert len(expanded_ct) == len(labeled_ct), \
        ("Mismatch after expanding labels, expanded_ct.rows = %s != labeled_ct.rows %s" %
            (len(expanded_ct), len(labeled_ct)))
    print("After expanding, columns went from %s -> %s" %
        (len(labeled_ct.columns), len(expanded_ct.columns)))
    assert len(expanded_ct.columns) == len(labeled_ct.columns) + labels_per_trip, \
        ("Mismatch after expanding labels, expanded_ct.columns = %s != labeled_ct.columns %s" %
            (len(expanded_ct.columns), len(labeled_ct.columns)))
    disp.display(expanded_ct.head())
    return expanded_ct

def expand_inferredlabels(labeled_inferred_ct):
    if len(labeled_inferred_ct) == 0:
        return labeled_inferred_ct

    def _select_max_label(row):
        if row['user_input']:
            return row['user_input']
        max_entry = max(row['inferred_labels'], key=lambda x: x['p'])
        return max_entry['labels'] if max_entry['p'] > row['confidence_threshold'] else {
            'mode_confirm': 'uncertain'
        }

    labeled_inferred_labels = labeled_inferred_ct.apply(_select_max_label, axis=1).apply(pd.Series)
    disp.display(labeled_inferred_labels.head())
    expanded_labeled_inferred_ct = pd.concat([labeled_inferred_ct, labeled_inferred_labels], axis=1)
    # Filter out the dataframe in which mode_confirm is uncertain
    expanded_labeled_inferred_ct = expanded_labeled_inferred_ct[(expanded_labeled_inferred_ct['mode_confirm'] != 'uncertain')]
    disp.display(expanded_labeled_inferred_ct.head())
    return expanded_labeled_inferred_ct

# CASE 2 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
unique_users = lambda df: len(df.user_id.unique()) if "user_id" in df.columns else 0
trip_label_count = lambda s, df: len(df[s].dropna()) if s in df.columns else 0

async def load_viz_notebook_data(year, month, program, study_type, labels, include_test_users=False, add_footprint=False):
    #TODO - see how slow the loading the footprint is compared to just the baseMode, and evaluate if passing param around is needed
    """ Inputs:
    year/month/program/study_type = parameters from the visualization notebook
    dic_* = label mappings; if dic_pur is included it will be used to recode trip purpose

    Pipeline to load and process the data before use in visualization notebooks.
    """
    # Access database
    tq = get_time_query(year, month)
    participant_ct_df = await load_all_participant_trips(program, tq, include_test_users, labels, add_footprint)
    labeled_ct = filter_labeled_trips(participant_ct_df)
    expanded_ct = expand_userinputs(labeled_ct)
    expanded_ct = data_quality_check(expanded_ct)
    expanded_ct = map_trip_data(expanded_ct, study_type, labels)

    # Document data quality
    file_suffix = get_file_suffix(year, month, program)
    quality_text = get_quality_text(participant_ct_df, expanded_ct, None, include_test_users)

    debug_df = pd.DataFrame.from_dict({
            "year": year,
            "month": month,
            "Registered_participants": len(get_participant_uuids(program, include_test_users)),
            "Participants_with_at_least_one_trip": unique_users(participant_ct_df),
            "Participant_with_at_least_one_labeled_trip": unique_users(labeled_ct),
            "Trips_with_at_least_one_label": len(labeled_ct),
            "Trips_with_mode_confirm_label": trip_label_count("mode_confirm_w_other", expanded_ct),
            "Trips_with_trip_purpose_label": trip_label_count("purpose_confirm_w_other", expanded_ct),
            "Trips_with_replaced_mode_label": trip_label_count("replaced_mode_w_other", expanded_ct)
            },
        orient='index', columns=["value"])

    return expanded_ct, file_suffix, quality_text, debug_df

def map_trip_data(expanded_trip_df, study_type, labels):
    # Change meters to miles
    # CASE 2 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if "distance" in expanded_trip_df.columns:
        unit_conversions(expanded_trip_df)

    # Map new mode labels with translations dictionary from dynamic_labels
    # CASE 2 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if "mode_confirm" in expanded_trip_df.columns:
        # If the 'mode_confirm' is not available as the list of keys in the dynamic_labels or label_options.default.json, then, we should transform it as 'other'
        mode_values = [item['value'] for item in labels['MODE']]
        expanded_trip_df['mode_confirm_w_other'] = expanded_trip_df['mode_confirm'].apply(lambda mode: 'other' if mode not in mode_values else mode)
    if study_type == 'program':
        # CASE 2 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
        if 'replaced_mode' in expanded_trip_df.columns:
            replaced_modes = [item['value'] for item in labels['REPLACED_MODE']]
            expanded_trip_df['replaced_mode_w_other'] = expanded_trip_df['replaced_mode'].apply(lambda mode: 'other' if mode not in replaced_modes else mode)
        else:
            print("This is a program, but no replaced modes found. Likely cold start case. Ignoring replaced mode mapping")
    else:
            print("This is a study, not expecting any replaced modes.")

    # Trip purpose mapping
    # CASE 2 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if "purpose_confirm" in expanded_trip_df.columns:
        purpose_values = [item['value'] for item in labels['PURPOSE']]
        expanded_trip_df['purpose_confirm_w_other'] = expanded_trip_df['purpose_confirm'].apply(lambda value: 'other' if value not in purpose_values else value)

    return expanded_trip_df

async def load_viz_notebook_inferred_data(year, month, program, study_type, labels, include_test_users=False, add_footprint=False):
    """ Inputs:
    year/month/program/study_type = parameters from the visualization notebook
    dic_* = label mappings; if dic_pur is included it will be used to recode trip purpose

    Pipeline to load and process the data before use in visualization notebooks.
    """
    # Access database
    tq = get_time_query(year, month)
    participant_ct_df = await load_all_participant_trips(program, tq, include_test_users, labels, add_footprint)
    inferred_ct = filter_inferred_trips(participant_ct_df)
    expanded_it = expand_inferredlabels(inferred_ct)
    expanded_it = map_trip_data(expanded_it, study_type, labels)

    # Document data quality
    file_suffix = get_file_suffix(year, month, program)
    quality_text = get_quality_text(participant_ct_df, expanded_it, None, include_test_users)

    debug_df = pd.DataFrame.from_dict({
            "year": year,
            "month": month,
            "Registered_participants": len(get_participant_uuids(program, include_test_users)),
            "Participants_with_at_least_one_trip": unique_users(participant_ct_df),
            "Participant_with_at_least_one_inferred_trip": unique_users(inferred_ct),
            "Trips_with_at_least_one_inferred_label": len(inferred_ct),
            "Trips_with_mode_confirm_inferred_label": trip_label_count("mode_confirm_w_other", expanded_it),
            "Trips_with_trip_purpose_inferred_label": trip_label_count("purpose_confirm_w_other", expanded_it),
            "Trips_with_replaced_mode_inferred_label": trip_label_count("replaced_mode_w_other", expanded_it)
            },
        orient='index', columns=["value"])

    return expanded_it, file_suffix, quality_text, debug_df

# Function to map the "MODE", "REPLACED_MODE", "PURPOSE" to respective en-translations
# Input: dynamic_labels, label_type: MODE, REPLACED_MODE, PURPOSE
# Return: Dictionary mapping between the label type and its english translation.
def mapping_labels(dynamic_labels, label_type):
    if "translations" in dynamic_labels and "en" in dynamic_labels["translations"]:
        translations = dynamic_labels["translations"]["en"]
        dic_mapping = dict()

        def translate_labels(labels):
            translation_mapping = {}
            for label in labels:
                value = label["value"]
                translation = translations.get(value)
                translation_mapping[value] = translation
            return defaultdict(lambda: 'Other', translation_mapping)
        dic_mapping = translate_labels(dynamic_labels.get(label_type, ''))
        return dic_mapping

# Function: Maps "MODE", "PURPOSE", and "REPLACED_MODE" to colors.
# Input: dynamic_labels
# Output: Dictionary mapping between color with mode/purpose/sensed
def mapping_color_labels(labels = {}, unique_keys = []):
    sensed_values = ["WALKING", "BICYCLING", "IN_VEHICLE", "AIR_OR_HSR", "UNKNOWN", "OTHER", "INVALID"]

    # Load base mode values and purpose values
    mode_values =  [mode["value"] for mode in labels["MODE"]] if "MODE" in labels else []
    purpose_values = [mode["value"] for mode in labels["PURPOSE"]] if "PURPOSE" in labels else []
    replaced_values = [mode["value"] for mode in labels["REPLACED_MODE"]] if "REPLACED_MODE" in labels else []

    # Append 'other' to the list if not present
    for values in [mode_values, purpose_values, replaced_values]:
        if "other" not in values:
            values.append("other")

    # Mapping between mode values and base_mode OR baseMode (backwards compatibility)
    value_to_basemode = {mode["value"]: mode.get("base_mode", mode.get("baseMode", "UNKNOWN")) for mode in labels["MODE"]}
    # Assign colors to mode, replaced, purpose, and sensed values
    colors_mode = emcdb.dedupe_colors([
        [mode, emcdb.BASE_MODES[value_to_basemode.get(mode, "UNKNOWN")]['color']]
        for mode in set(mode_values)
    ], adjustment_range=[1,1.8])
    colors_replaced = emcdb.dedupe_colors([
        [mode, emcdb.BASE_MODES[value_to_basemode.get(mode, "UNKNOWN")]['color']]
        for mode in set(replaced_values)
    ], adjustment_range=[1,1.8])
    colors_purpose = dict(zip(purpose_values, plt.cm.tab20.colors[:len(purpose_values)]))
    colors_sensed = emcdb.dedupe_colors([
        [label, emcdb.BASE_MODES[label.upper()]['color'] if label.upper() != 'INVALID' else emcdb.BASE_MODES['UNKNOWN']['color']]
        for label in sensed_values
    ], adjustment_range=[1,1.8])
    colors_ble = emcdb.dedupe_colors([
        [label, emcdb.BASE_MODES[label]['color']]
        for label in set(unique_keys)
    ], adjustment_range=[1,1.8])
    return colors_mode, colors_replaced, colors_purpose, colors_sensed, colors_ble

def translate_values_to_labels(labels, language="en"):
    # Mapping between values and translations for display on plots (for Mode)
    values_to_translations_mode = mapping_labels(labels, "MODE")
    # Mapping between values and translations for display on plots (for Purpose)
    values_to_translations_purpose = mapping_labels(labels, "PURPOSE")
    # Mapping between values and translations for display on plots (for Replaced mode)
    values_to_translations_replaced = mapping_labels(labels, "REPLACED_MODE")

    # Add "other": "Other" to the values_to_translations_* dictionary if "other" key is unavailable
    for dict_update in [values_to_translations_mode, values_to_translations_purpose, values_to_translations_replaced]:
        dict_update.setdefault("other", "Other")

    return values_to_translations_mode, values_to_translations_purpose, values_to_translations_replaced

# Function: Maps survey answers to colors.
# Input: dictionary of raw and translated survey answers
# Output: Map for color with survey answers
def mapping_color_surveys(dic_options):
    dictionary_values = (list(OrderedDict.fromkeys(dic_options.values())))
    
    colors = {}
    for i in range(len(dictionary_values)):
        colors[dictionary_values[i]] = plt.cm.tab10.colors[i%10]
    
    colors['Other'] = plt.cm.tab10.colors[(i+1)%10]

    return colors

async def load_viz_notebook_sensor_inference_data(year, month, program, labels, include_test_users=False, sensed_algo_prefix="cleaned"):
    """ Inputs:
    year/month/program = parameters from the visualization notebook

    Pipeline to load and process the data before use in sensor-based visualization notebooks.
    """
    tq = get_time_query(year, month)
    participant_ct_df = await load_all_participant_trips(program, tq, include_test_users, labels, False)
    expanded_ct = participant_ct_df
    print(f"Loaded expanded_ct with length {len(expanded_ct)} for {tq}")
    
    #TODO-this is also in the admin dash, can we unify?
    get_max_mode_from_summary = lambda md: (
            "INVALID"
            if not isinstance(md, dict)
            or "distance" not in md
            or not isinstance(md["distance"], dict)
            # If 'md' is a dictionary and 'distance' is a valid key pointing to a dictionary:
            else (
                # Get the maximum value from 'md["distance"]' using the values of 'md["distance"].get' as the key for 'max'.
                # This operation only happens if the length of 'md["distance"]' is greater than 0.
                # Otherwise, return "INVALID".
                max(md["distance"], key=md["distance"].get)
                if len(md["distance"]) > 0
                else "INVALID"
            )
        )
    
    if len(expanded_ct) > 0:
        expanded_ct["primary_mode_non_other"] = participant_ct_df.cleaned_section_summary.apply(get_max_mode_from_summary)
        expanded_ct.primary_mode_non_other.replace({"ON_FOOT": "WALKING"}, inplace=True)
        valid_sensed_modes = ["WALKING", "BICYCLING", "IN_VEHICLE", "AIR_OR_HSR", "UNKNOWN", "INVALID"]
        expanded_ct["primary_mode"] = expanded_ct.primary_mode_non_other.apply(lambda pm: "OTHER" if pm not in valid_sensed_modes else pm)

    # Change meters to miles
    # CASE 2 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    if "distance" in expanded_ct.columns:
        unit_conversions(expanded_ct)

    # Document data quality
    file_suffix = get_file_suffix(year, month, program)
    quality_text = get_quality_text_sensed(expanded_ct, "", include_test_users)

    debug_df = pd.DataFrame.from_dict({
            "year": year,
            "month": month,
            "Registered_participants": len(get_participant_uuids(program, include_test_users)),
            "Participants_with_at_least_one_trip": unique_users(participant_ct_df),
            "Number of trips": len(participant_ct_df),
            },
        orient='index', columns=["value"])

    return expanded_ct, file_suffix, quality_text, debug_df

async def load_viz_notebook_survey_data(year, month, program, labels, include_test_users=False):
    """ Inputs:
    year/month/program/test users = parameters from the visualization notebook

    Returns: df of all trips taken by participants, df of all trips with user_input
    """
    tq = get_time_query(year, month)
    participant_ct_df = await load_all_participant_trips(program, tq, include_test_users, labels, False)
    labeled_ct = filter_labeled_trips(participant_ct_df)
    
    # Document data quality
    file_suffix = get_file_suffix(year, month, program)
    
    return participant_ct_df, labeled_ct, file_suffix

def get_quality_text(before_df, after_df, mode_of_interest=None, include_test_users=False):
    """ Inputs:
    before_df = dataframe prior to filtering (usually participant_ct_df)
    after_df = dataframe after filtering (usually expanded_ct)
    mode_of_interest = optional detail to include in the text string
    """
    # CASE 1 of https://github.com/e-mission/em-public-dashboard/issues/69#issuecomment-1256835867
    after_pct = (len(after_df) * 100) / len(before_df) if len(before_df) != 0 else np.nan
    cq = (len(after_df), unique_users(after_df), len(before_df), unique_users(before_df),
        after_pct, )
    interest_str = mode_of_interest + ' ' if mode_of_interest is not None else ''
    total_str = 'confirmed' if mode_of_interest is not None else ''
    user_str = 'testers and participants' if include_test_users else 'users'
    quality_text = f"Based on %s confirmed {interest_str}trips from %d {user_str}\nof %s total {total_str} trips from %d users (%.2f%%)" % cq
    print(quality_text)
    return quality_text

def get_quality_text_sensed(df, cutoff_text="", include_test_users=False):
    cq = (len(df), unique_users(df))
    user_str = 'testers and participants' if include_test_users else 'users'
    quality_text = f"Based on %s trips ({cutoff_text}) from %d {user_str}" % cq if cutoff_text else f"Based on %s trips from %d {user_str}" % cq
    print(quality_text)
    return quality_text

#once we can calculate the "denominator" for survey trips, this can be removed
def get_quality_text_numerator(df, include_test_users=False):
    cq = (len(df), unique_users(df))
    user_str = 'testers and participants' if include_test_users else 'users'
    quality_text = f"Based on %s trips from %d {user_str}" % cq
    print(quality_text)
    return quality_text

def get_file_suffix(year, month, program):
    suffix = "_%04d" % year if year is not None else ""
    suffix = suffix + "_%02d" % month if month is not None else ""
    suffix = suffix + "_%s" % program if program is not None else ""
    print(suffix)
    return suffix

def data_quality_check(expanded_ct):
    '''1. Delete rows where the mode_confirm was pilot_ebike and repalced_mode was pilot_ebike.
       2. Delete rows where the mode_confirm was pilot_ebike and repalced_mode was same_mode.
       3. Replace same_mode for the mode_confirm for Energy Impact Calcualtion.'''

    # TODO: This is only really required for the initial data collection around the minipilot
    # in subsequent deployes, we removed "same mode" and "pilot_ebike" from the options, so the
    # dataset did not contain of these data quality issues

    if 'replaced_mode' in expanded_ct.columns:
        expanded_ct.drop(expanded_ct[(expanded_ct['mode_confirm'] == 'pilot_ebike') & (expanded_ct['replaced_mode'] == 'pilot_ebike')].index, inplace=True)
        expanded_ct.drop(expanded_ct[(expanded_ct['mode_confirm'] == 'pilot_ebike') & (expanded_ct['replaced_mode'] == 'same_mode')].index, inplace=True)
        expanded_ct['replaced_mode'] = np.where(expanded_ct['replaced_mode'] == 'same_mode',expanded_ct['mode_confirm'], expanded_ct['replaced_mode'])
    
    return expanded_ct

def unit_conversions(df):
    df['distance_miles']= df["distance"]*0.00062 #meters to miles
    df['distance_kms'] = df["distance"] / 1000 #meters to kms

def extract_footprint(footprint_dict, footprint_key):
    if footprint_key in footprint_dict.keys():
        return footprint_dict[footprint_key]
    else:
        return np.nan

def unpack_energy_emissions(expanded_ct, use_imperial):
    expanded_ct['mode_confirm_CO2'] = expanded_ct['mode_confirm_footprint'].apply(extract_footprint, footprint_key='kg_co2')
    expanded_ct['replaced_mode_CO2'] = expanded_ct['replaced_mode_footprint'].apply(extract_footprint, footprint_key='kg_co2')
    if use_imperial:
        expanded_ct['mode_confirm_CO2'] = kg_to_lb(expanded_ct['mode_confirm_CO2'])
        expanded_ct['replaced_mode_CO2'] = kg_to_lb(expanded_ct['replaced_mode_CO2'])
    CO2_impact(expanded_ct)

    expanded_ct['replaced_mode_EI'] = expanded_ct['replaced_mode_footprint'].apply(extract_footprint, footprint_key='kwh')
    expanded_ct['mode_confirm_EI'] = expanded_ct['mode_confirm_footprint'].apply(extract_footprint, footprint_key='kwh')
    energy_impact(expanded_ct)

    return expanded_ct

def energy_impact(df):
    df['Energy_Impact']  = round((df['replaced_mode_EI'] - df['mode_confirm_EI']),3)

def kg_to_lb(kg):
    return kg * 2.20462

def CO2_impact(df):
    df['CO2_Impact']  = round((df['replaced_mode_CO2'] - df['mode_confirm_CO2']), 3)
    return df

# Function to print the emission calculations in both Metric and Imperial System. Helps in debugging for emission calculation.
# Used this function specifically to test with label_options: https://github.com/e-mission/op-deployment-configs/blob/main/label_options/example-program-label-options.json
# Config: https://github.com/e-mission/op-deployment-configs/blob/main/configs/dev-emulator-program.nrel-op.json
def print_CO2_emission_calculations(data_eb, ebco2_lb, ebco2_kg, dynamic_labels):
    #TODO update this function with new columns after switching to emcommon emissions
    filtered_taxi_data = data_eb[data_eb['Replaced_mode'] == "Taxi/Uber/Lyft"]
    filtered_bus_data = data_eb[data_eb['Replaced_mode'] == "Bus"]
    filtered_freeshuttle_data = data_eb[data_eb['Replaced_mode'] == "Free Shuttle"]
    filtered_walk_data = data_eb[data_eb['Replaced_mode'] == "Walk"]

    # Handling different cases of Replaced mode translations
    if len(dynamic_labels) > 0:
        filtered_GasCarShared_data = data_eb[data_eb['Replaced_mode'] == "Gas Car Shared Ride"]
        filtered_notravel_data = data_eb[data_eb['Replaced_mode'] == "No travel"]
        print("With Dynamic Config:")
        print("\n")
    else:
        filtered_GasCarShared_data = data_eb[data_eb['Replaced_mode'] == "Gas Car, with others"]
        filtered_notravel_data = data_eb[data_eb['Replaced_mode'] == "No Travel"]
        print("With Default mapping:")
        print("\n")

    selected_columns = ['distance','distance_miles', 'replaced_mode_footprint_kg_co2', 'mode_comfirm_footprint_kg_co2', "replaced_mode", "mode_confirm"]

    print("Walk Data:")
    print(str(filtered_walk_data[selected_columns].head()))
    print("\n")

    print("No Travel Data:")
    print(str(filtered_notravel_data[selected_columns].head()))
    print("\n")

    print("Gas Car Shared Data:")
    print(str(filtered_GasCarShared_data[selected_columns].head()))
    print("\n")

    print("Free Shuttle Data:")
    print(str(filtered_freeshuttle_data[selected_columns].head()))
    print("\n")

    print("Bus Data:")
    print(str(filtered_bus_data[selected_columns].head()))
    print("\n")

    print("Taxi/Uber/Lyft Data:")
    print(str(filtered_taxi_data[selected_columns].head()))
    print("\n")

    combined_df = pd.concat([ebco2_lb['total_lb_CO2_emissions'], ebco2_kg['total_kg_CO2_emissions']], axis=1)
    combined_df.columns = ['Total CO2 Emissions (lb)', 'Total CO2 Emissions (kg)']

    print("CO2 Emissions:")
    print(combined_df)

'''
input: boolean (True = use miles & false = use kms, etc)
returns: four Strings used to handle units in the notebooks
'''
def get_units(use_imperial):
    if use_imperial:
        label_units = "Miles"
        short_label = "miles"
        weight_unit = "lb"
    else:
        label_units = "Kilometers"
        short_label = "kms"
        weight_unit = "kg"

    label_units_lower = label_units.lower()
    distance_col = "distance_" + short_label
    
    return label_units, short_label, label_units_lower, distance_col, weight_unit
