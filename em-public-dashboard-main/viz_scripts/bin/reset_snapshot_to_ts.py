## This is a standalone script that resets the database to a previously
## specified timestamp. It does so by deleting entries after the timestamp,
## and removing labels that were entered after the timestamp as well

import argparse
import arrow
import logging
import sys

import emission.storage.decorations.user_queries as ecdu
import emission.core.wrapper.entry as ecwe
import emission.core.wrapper.pipelinestate as ecwp
import emission.core.get_database as edb

import emission.storage.decorations.trip_queries as esdt
import emission.storage.timeseries.timequery as estt
import emission.storage.timeseries.abstract_timeseries as esta

if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(prog="export_participants_trips")
    parser.add_argument("reset_fmt_time", help="reset timestamp in the format displayed on the metrics you are trying to match - e.g. 'YYYY-MM-DDThh:mm:ss.ms+00:00'")
    parser.add_argument("-z", "--timezone", help="timezone to format the pipeline state timestamps in", default="UTC")

    args = parser.parse_args()
    reset_ts = arrow.get(args.reset_fmt_time).timestamp()
    print(f"After parsing, the reset timestamp is {args.reset_fmt_time} -> {reset_ts}")

    #first, count all entries written after a cutoff time
    print(f"Planning to delete {edb.get_timeseries_db().count_documents({ 'metadata.write_ts': { '$gt': reset_ts } })} records from the timeseries")
    print(f"Planning to delete {edb.get_analysis_timeseries_db().count_documents({ 'metadata.write_ts': { '$gt': reset_ts } })} records from the analysis timeseries")
    
    #then, find manual inputs added after the cutoff time
    print(f"number of manual records after cutoff {(edb.get_timeseries_db().count_documents({'metadata.write_ts': {'$gt': reset_ts}, 'metadata.key': {'$regex': '^manual/(mode_confirm|purpose_confirm|replaced_mode)$'}}))}")
    for user_id in ecdu.get_all_uuids():
        mi_pipeline_state = edb.get_pipeline_state_db().find_one({"user_id": user_id,
            "pipeline_stage": ecwp.PipelineStages.USER_INPUT_MATCH_INCOMING.value})
        if mi_pipeline_state is None:
            print(f"for {user_id}, USER_INPUT_MATCH_INCOMING was never run")
        else:
            print(f"for {user_id}, USER_INPUT_MATCH_INCOMING was last run at {arrow.get(mi_pipeline_state['last_ts_run']).to(args.timezone)}")

        cc_pipeline_state = edb.get_pipeline_state_db().find_one({"user_id": user_id,
            "pipeline_stage": ecwp.PipelineStages.CREATE_CONFIRMED_OBJECTS.value})
        if cc_pipeline_state is None:
            print(f"for {user_id}, CREATE_CONFIRMED_OBJECTS was never run")
        else:
            print(f"for {user_id}, CREATE_CONFIRMED_OBJECT was last run at {arrow.get(cc_pipeline_state['last_ts_run']).to(args.timezone)}")

        ts = esta.TimeSeries.get_time_series(user_id)
        fully_reset = {}
        direct_count = (edb.get_timeseries_db().count_documents({'user_id': user_id,
            'metadata.write_ts': {'$gt': reset_ts},
            'metadata.key': {'$regex': '^manual/(mode_confirm|purpose_confirm|replaced_mode)$'}}))
        timeseries_count = ts.find_entries_count(
            ["manual/mode_confirm", "manual/purpose_confirm", "manual/replaced_mode"],
            estt.TimeQuery("metadata.write_ts", reset_ts, sys.maxsize))
        print(f"number of manual records after cutoff = direct: {direct_count}, timeseries: {timeseries_count}")
        assert direct_count == timeseries_count,\
            f"number of manual records after cutoff = direct: {direct_count}, timeseries: {timeseries_count}"
        for ui in ts.find_entries(["manual/mode_confirm", "manual/purpose_confirm", "manual/replaced_mode"],
            estt.TimeQuery("metadata.write_ts", reset_ts, sys.maxsize)):
            confirmed_trip = esdt.get_confirmed_obj_for_user_input_obj(ts, ecwe.Entry(ui))
            if confirmed_trip is None:
                print("No matching confirmed trip for %s" % ui["data"]["start_fmt_time"])
                # if the user is labeling a processed trip, then there must be
                # a confirmed_trip entry that will match it. If there is no
                # match, then the trip must still be a draft
                if cc_pipeline_state["last_processed_ts"] < ui["data"]["start_ts"]:
                    print(f"last processed confirmed trip was at {arrow.get(cc_pipeline_state['last_processed_ts']).to(args.timezone)} but the user labeled input submitted at {arrow.get(ui['metadata']['write_ts']).to(args.timezone)} starting at {ui['data']['start_fmt_time']}, user labeled a draft trip, so will not be a confirmed trip to match")
                else:
                    assert False,\
                        f"last processed confirmed trip was at {arrow.get(cc_pipeline_state['last_processed_ts']).to(args.timezone)} after the user input submitted at {arrow.get(ui['metadata']['write_fmt_time'])} starting at {ui['data']['start_fmt_time']}, , user labeled a draft trip, so there should be a confirmed trip to match"
            elif confirmed_trip["data"]["user_input"] == {}:
                print(f"For input {ui['data']['start_fmt_time']} of type {ui['metadata']['key']}, labeled at {arrow.get(ui['metadata']['write_fmt_time'])}, found confirmed trip {confirmed_trip['_id']} starting at {confirmed_trip['data']['start_fmt_time']} with no user input")
                # no match implies:
                # user input was not available when trip was created and
                # user input has not been processed since trip was created
                if confirmed_trip["metadata"]["write_ts"] > mi_pipeline_state["last_processed_ts"] and \
                    confirmed_trip["metadata"]["write_ts"] < ui["metadata"]["write_ts"]:
                    print(f"confirmed trip {confirmed_trip['_id']} was written after the last matching pipeline run {arrow.get(ui['metadata']['write_ts']).to(args.timezone)}, and before user input was written {arrow.get(ui['metadata']['write_ts']).to(args.timezone)}, could not have been filled in")
                else:
                    if fully_reset.get(confirmed_trip["_id"], False):
                        print(f"confirmed trip {confirmed_trip['_id']} used to have matching inputs but has been fully reset")
                    else:
                        # so if user input was available before trip creation or
                        # matching input was run after trip creation, it should
                        # have matched
                        assert False,\
                            f"confirmed trip {confirmed_trip['_id']} was written {arrow.get(confirmed_trip['metadata']['write_ts']).to(args.timezone)} before the last matching pipeline run {arrow.get(mi_pipeline_state['last_processed_ts']).to(args.timezone)}, or after user input was written {arrow.get(ui['metadata']['write_ts']).to(args.timezone)}, should have been filled in"
            else:
                print(f"For input {ui['data']['start_fmt_time']} of type {ui['metadata']['key']}, labeled at {arrow.get(ui['metadata']['write_fmt_time'])}, found confirmed trip {confirmed_trip['_id']} starting at {confirmed_trip['data']['start_fmt_time']} with user input {confirmed_trip['data']['user_input']}")
                assert confirmed_trip["data"]["start_ts"] == ui["data"]['start_ts'],\
                    "MATCHING CONFIRMED TRIP {confirmed_trip['_id']} WITH USER INPUT AND DIFFERENT TS"
                input_type = ui["metadata"]["key"].split("/")[1]
                print(f"Resetting input of type {input_type}")
                update_results = edb.get_analysis_timeseries_db().update_one({"_id": confirmed_trip["_id"],
                    "metadata.key": "analysis/confirmed_trip"}, { "$unset": { 'data.user_input.%s' % input_type: {} } })
                # mark whether the trip has been complete reset
                fully_reset[confirmed_trip["_id"]] = edb.get_analysis_timeseries_db().find_one(
                    {"_id": confirmed_trip["_id"]})["data"]["user_input"] == {}
                    
                print(f"Update results = {update_results.raw_result}")

    print(f"delete all entries after timestamp {reset_ts}")
    print(f"deleting all timeseries entries after {reset_ts}, {edb.get_timeseries_db().delete_many({ 'metadata.write_ts': { '$gt': reset_ts } }).raw_result}")
    print(f"deleting all analysis timeseries entries after {reset_ts}, {edb.get_analysis_timeseries_db().delete_many({ 'metadata.write_ts': { '$gt': reset_ts } }).raw_result}")

