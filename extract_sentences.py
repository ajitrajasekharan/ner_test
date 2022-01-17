#!/usr/bin/python3
import time
import math
import sys
import pdb
import requests
import urllib
from  collections import OrderedDict
import argparse
import config_utils as cf
import common as utils
import requests
import json

def accrue_unique_mismatched_phrases(stats_dict,orig_sent_arr,terms_arr,span_arr,mask_tag):
    TAG_POS = 2
    END_POS = 4
    assert(len(span_arr) == len(terms_arr))
    index = 0
    curr_span = []
    actuals = []
    for tag,actual in zip(orig_sent_arr,terms_arr):
        if (tag.endswith(mask_tag)):
            if(span_arr[index] == 1):
                curr_span.append(terms_arr[index][TAG_POS])
                if (len(actuals) == 0):
                    run_i = index
                    while (run_i >= 0):
                        if (span_arr[run_i] == 1):
                            run_i -= 1
                        else:
                            run_i += 1
                            break
                    if (run_i < 0):
                        run_i += 1
                    else:
                        assert(span_arr[run_i] == 1)
                    while (run_i < len(span_arr)):
                        if (span_arr[run_i] == 1):
                            actuals.append(terms_arr[run_i][TAG_POS])
                            run_i += 1
                        else:
                            break
            else:
                print("Tagging a position that is not even a noun entity according to POS tagger.Skipping accrual")
                return
        else:
            if (len(curr_span) != 0):
                curr_phrase = '_'.join(curr_span)
                if (curr_phrase not in stats_dict["unique_phrases"]):
                    stats_dict["unique_phrases"][curr_phrase] = {"count":1,"actuals": {}}
                else:
                    stats_dict["unique_phrases"][curr_phrase]["count"] += 1
                if (len(actuals) > 0):
                    actuals_phrase = '_'.join(actuals)
                    if (actuals_phrase not in stats_dict["unique_phrases"][curr_phrase]["actuals"]):
                        stats_dict["unique_phrases"][curr_phrase]["actuals"] = actuals_phrase
                curr_span = []
                actuals = []
        index += 1

    if (len(curr_span) != 0):
        curr_phrase = '_'.join(curr_span)
        if (curr_phrase not in stats_dict["unique_phrases"]):
            stats_dict["unique_phrases"][curr_phrase] = {"count":1,"actuals": {}}
        else:
            stats_dict["unique_phrases"][curr_phrase]["count"] += 1
            if (len(actuals) > 0):
                actuals_phrase = '_'.join(actuals)
                if (actuals_phrase not in stats_dict["unique_phrases"][curr_phrase]["actuals"]):
                    stats_dict["unique_phrases"][curr_phrase]["actuals"] = actuals_phrase
        
    

POS_TERM_POS =  1
POS_TAG_POS = 2
def get_stats(gen_st,stats_dict,sent,pos_server_url,mask_tag,sample_count):
    if (gen_st):
        print(str(stats_dict["total"]) + " of  " + str(sample_count))
        if (stats_dict["total"] >= sample_count):
            return
        orig_sent_arr = sent.replace('"','\'').split()
        url = pos_server_url  + sent.replace('"','\'').replace(mask_tag,"")
        r = dispatch_request(url)
        terms_arr = extract_POS(r.text)
        if (len(orig_sent_arr) != len(terms_arr)):
            if (len(terms_arr) + 1 == len(orig_sent_arr)):
                orig_sent_arr = orig_sent_arr[:-1]
            else:
                print("Skipping sentence")
                stats_dict["sent_length_mismatched"] += 1
                stats_dict["mismatched"] += 1
                stats_dict["total"] += 1
                return 
        assert(len(orig_sent_arr) == len(terms_arr))
        main_sent_arr,masked_sent_arr,span_arr = utils.detect_masked_positions(terms_arr)
        assert(len(span_arr) == len(orig_sent_arr))
        matched = True
        span_in_progress = False
        for s,t in zip(span_arr,orig_sent_arr):
            if (s == 1):
                if (t.endswith(mask_tag)):
                    span_in_progress = True
                    continue
                else:
                    if (span_in_progress):
                        matched = False;
                        break
                    else:
                        span_in_progress = False
            else:
                if (t.endswith(mask_tag)):
                    if (span_in_progress):
                        matched = False;
                        break
                span_in_progress = False
        if (not matched):
            stats_dict["mismatched"] += 1
            accrue_unique_mismatched_phrases(stats_dict,orig_sent_arr,terms_arr,span_arr,mask_tag)
        stats_dict["total"] += 1

def dispatch_request(url):
    max_retries = 10
    attempts = 0
    while True:
        try:
            r = requests.get(url,timeout=1000)
            if (r.status_code == 200):
                return r
        except:
            print("Request:", url, " failed. Retrying...")
        attempts += 1
        if (attempts >= max_retries):
            print("Request:", url, " failed")
            break

#This is bad hack for prototyping - parsing from text output as opposed to json
def extract_POS(text):
    arr = text.split('\n')
    if (len(arr) > 0):
        start_pos = 0
        for i,line in enumerate(arr):
            if (len(line) > 0):
                start_pos += 1
                continue
            else:
                break
        #print(arr[start_pos:])
        terms_arr = []
        for i,line in enumerate(arr[start_pos:]):
            terms = line.split('\t')
            if (len(terms) == 5):
                #print(terms)
                terms_arr.append(terms)
        return terms_arr

def output_stats(stats_output_file,stats_dict):
    stats_dict["mismatched_percent"] = round((float(stats_dict["mismatched"])/stats_dict["total"])*100,2)
    stats_dict["sent_length_mismatched_percent"] = round((float(stats_dict["sent_length_mismatched"])/stats_dict["total"])*100,2)
    with open(stats_output_file,"w") as sfp:
        sfp.write(json.dumps(stats_dict,indent=4) + "\n")
        print(json.dumps(stats_dict,indent=4))


def extract(param):
    input_file = cf.read_config(param.config)["input_file"]
    output_file = cf.read_config(param.config)["output_file"]
    stats_output_file = cf.read_config(param.config)["stats_output_file"]
    label_index = cf.read_config(param.config)["label_index"]
    term_index = cf.read_config(param.config)["term_index"]
    mask_tag = cf.read_config(param.config)["MASK_TAG"]
    prefix_b_tag = cf.read_config(param.config)["PREFIX_B_TAG"]
    prefix_i_tag = cf.read_config(param.config)["PREFIX_I_TAG"]
    gen_st = param.gen_stats
    pos_server_url  = cf.read_config(param.config)["POS_SERVER_URL"]
    phrase_span_sample = param.sample
    max_val = label_index if label_index > term_index else term_index
    max_val = label_index if label_index > term_index else term_index
    
    wfp = open(output_file,"w")
    stats_dict = {"total":0,"mismatched":0,"sent_length_mismatched":0,"unique_phrases":{}}
    with open(input_file) as fp:
        accrued_line_arr = []
        for line in fp:
            line = line.rstrip()
            line = line.split()
            if (len(line) >= max_val):
                if (line[label_index].startswith(prefix_b_tag) or line[label_index].startswith(prefix_i_tag)):
                    accrued_line_arr.append(line[term_index] + mask_tag)
                else:
                    accrued_line_arr.append(line[term_index])
            else:
                if (len(accrued_line_arr) > 0):
                    #print(' '.join(accrued_line_arr))
                    wfp.write(' '.join(accrued_line_arr) + "\n")
                    get_stats(gen_st,stats_dict,' '.join(accrued_line_arr),pos_server_url,mask_tag,phrase_span_sample)
                    
                    accrued_line_arr = []
        if (len(accrued_line_arr) > 0):
            #print(' '.join(accrued_line_arr))
            wfp.write(' '.join(accrued_line_arr) + "\n")
            get_stats(gen_st,stats_dict,' '.join(accrued_line_arr),pos_server_url,mask_tag,phrase_span_sample)

    if (gen_st):
        output_stats(stats_output_file,stats_dict)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Conversion utility to extract sentences from columnar format input file  ',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-config', action="store", dest="config",default="extract_config.json",help='Defaul config file for extract params')
    parser.add_argument('-gen_stats', dest="gen_stats", action='store_true',help='Generate stats of phrases spans of labeled terms')
    parser.add_argument('-no-gen_stats', dest="gen_stats", action='store_false',help='Do not generate stats of phrases spans of labeled terms')
    parser.add_argument('-sample', dest="sample", action='store',type=int,default=1000,help='Default count of phrase span sentence sampling')
    parser.set_defaults(gen_stats=True)
    results = parser.parse_args()

    extract(results)
