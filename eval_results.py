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
import json

def get_sentence(fp):
    ret_arr = []
    while (True):
        line = fp.readline().rstrip().split()
        if (len(line) == 0):
            break
        ret_arr.append(line)
    return ret_arr

def   reconcile_tokenization_differences(gr_line,result_line,g_term_index,g_label_index,r_term_index,r_label_index):
    if (len(gr_line) != len(result_line)):
        if (len(gr_line) == len(result_line) - 1):
            if (result_line[-1][r_term_index] == '.'):
                return True,gr_line,result_line[:-1]
        if (len(gr_line) < len(result_line)):
            #print("Greater")
            new_result_line = []
            j = 0
            for i in range(len(gr_line)):
                word = gr_line[i][g_term_index]
                concatenated_word = ""
                while (j < len(result_line)):
                    concatenated_word = concatenated_word + result_line[j][r_term_index]
                    if (word.lower() == concatenated_word.lower()):
                            val = result_line[j]
                            val[r_term_index] = concatenated_word
                            new_result_line.append(val)
                            j += 1
                            break
                    j += 1
            ret_val = True if (len(gr_line) == len(new_result_line)) else False
            return ret_val,gr_line,new_result_line
        else:
            #print("Lesser!")
            #pdb.set_trace()
            min_val = len(result_line)
            gr_line = gr_line[:min_val]
            return True,gr_line,result_line
    else:
        return True,gr_line,result_line
    assert(0)
    return False,gr_line,result_line

def output_resynced_results(fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index):
    for g,a in zip(gr_sent,result_sent):
        fp.write(g[g_term_index] + " " + g[g_label_index] + " " + a[r_label_index] + "\n")
    fp.write("\n")

def output_passed_results(fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index):
    for g,a in zip(gr_sent,result_sent):
        a_label = "O" if g[g_label_index] == "O" else a[r_label_index] #this is to avoid ease of browsing passed results. Note given we label all entity types for sentences without a tag, since the test set looks only for a specific entity type
                                                                       #we consider false positives only the case where the ground truth is "O" and the model prediction is the entity type being tested. 
        fp.write(g[g_term_index] + " " + g[g_label_index] + " " + a_label + "\n")
    fp.write("\n")

def output_oos_sentence(fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index):
    for g in gr_sent:
        fp.write(g[g_term_index] + " ")
    fp.write("\n")
    for r in result_sent:
        fp.write(r[r_term_index] + " ")
    fp.write("\n\n")


def construct_cf_matrix(entity_mapping):
    results_dict = OrderedDict()
    results_dict["entity_counts"] = OrderedDict()
    results_dict["entities"] = OrderedDict()
    results_dict["stats"] = OrderedDict()
    results_dict["stats"]["tested_entity_count"] = 0
    results_dict["stats"]["dual_predictions"] = 0
    results_dict["stats"]["others_only_sentence_count"] = 0
    results_dict["stats"]["others_only_token_count"] = 0
    map_dict = OrderedDict()
    for key_i in range(len(entity_mapping)):
        row = OrderedDict()
        results_dict["entity_counts"][entity_mapping[key_i]["disp_name"] + "_count"] = 0
        results_dict["entities"][entity_mapping[key_i]["disp_name"]] = row
        map_dict[entity_mapping[key_i]["g_name"]]  =   {"disp_name": entity_mapping[key_i]["disp_name"], "map":entity_mapping[key_i]["map"] }
        for key_j in range(len(entity_mapping)):
            col = OrderedDict()
            row[entity_mapping[key_j]["disp_name"]] = 0
    return results_dict,map_dict

def prefix_strip(term):
    if (term.startswith("B_") or term.startswith("I_")):
        term = term[2:]
    else:
        if (term.startswith("B-") or term.startswith("I-")):
            term = term[2:]
    return term

def get_term(predictions):
    terms = predictions.split('/')
    ret_terms = []
    ret_sub_terms = []
    for term in terms:
        orig = term.rstrip(']')
        term = orig.split('[')[-1]
        sub_term = orig.split('[')[0]
        term = prefix_strip(term)
        sub_term = prefix_strip(sub_term)
        ret_terms.append(term)  
        ret_sub_terms.append(sub_term)  
        assert(len(ret_terms) == len(ret_sub_terms))
    return ret_terms,ret_sub_terms
        

def handle_false_positive (results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index,other_tag,ignore_false_positives):
    #Just pick the false positives for those entities in the ground truth set.
    failed = False
    results_dict["stats"]["others_only_sentence_count"] += 1
    for i in range(len(gr_sent)):
        results_dict["stats"]["others_only_token_count"] += 1
        results_dict["stats"]["tested_entity_count"] += 1
        results_dict["entity_counts"][map_dict[gr_sent[i][g_label_index]]["disp_name"] + "_count"] += 1
        g_label_unmapped = prefix_strip(gr_sent[i][g_label_index])
        g_label = map_dict[gr_sent[i][g_label_index]]["disp_name"]
        i_labels,i_sub_labels = get_term(result_sent[i][r_label_index])
        results_dict["stats"]["dual_predictions"] += 1 if (len(i_labels) == 2) else 0
        curr_failed = False
        for j in range(len(i_labels)):
            if (ignore_false_positives):
                break
            if (i_labels[j] != other_tag and i_labels[j] in fp_type_list and i_sub_labels[j] in fp_subtype_list):
                i_disp_label = fp_type_to_disp_map[i_labels[j]]
                results_dict["entities"][g_label][i_disp_label] += 1
                failed = True
                curr_failed = True
                break
            break #Just pick the first prediction when checking for fp
        if (not curr_failed):
            other_disp_tag = map_dict[other_tag]["disp_name"]
            results_dict["entities"][other_disp_tag][other_disp_tag] += 1
    return failed

def single_term_fp_check(results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index,other_tag,l_tag,i):
    g_label = map_dict[prefix_strip(gr_sent[i][g_label_index])]["disp_name"] 
    i_labels,i_sub_labels = get_term(result_sent[i][r_label_index])
    
    results_dict["stats"]["dual_predictions"] += 1 if (len(i_labels) == 2) else 0
    failed = False
    for j in range(len(i_labels)):
        if (i_labels[j] in fp_type_list and i_sub_labels[j] in fp_subtype_list):
            if (i_labels[j] != other_tag):
                i_disp_label = fp_type_to_disp_map[i_labels[j]]
                results_dict["entities"][g_label][i_disp_label] += 1
                #pdb.set_trace()
                failed = True
                break
        break #Just pick the first prediction when checking for fp
    if (not failed):
        disp_l_tag = map_dict[l_tag]["disp_name"]
        results_dict["entities"][disp_l_tag][disp_l_tag] += 1
    return failed

def in_alias_list(map_dict,g_label_unmapped,i_label):
    ret_val = False
    alias_arr = map_dict[g_label_unmapped]["map"]
    if (len(alias_arr) == 0):
            return True
    for i in range(len(alias_arr)):
        if (i_label in alias_arr[i]):
            return True
    return False

    
def eval_sentence(results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index,other_tag,misc_tag,strict_check,ignore_false_positives):
    all_others = True
    for i in range(len(gr_sent)):
        if (gr_sent[i][g_label_index] != other_tag):
            all_others = False
            break
    if (all_others): 
        return handle_false_positive(results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index,other_tag,ignore_false_positives)            
    #We come here only for sentences where ground truth is not all "O" 
    failed = False
    for i in range(len(gr_sent)):
        results_dict["stats"]["tested_entity_count"] += 1
        results_dict["entity_counts"][map_dict[prefix_strip(gr_sent[i][g_label_index])]["disp_name"] + "_count"] += 1
        if (gr_sent[i][g_label_index] != other_tag):
            #Ground truth is not "OTHER/O" if we come here
            g_label_unmapped = prefix_strip(gr_sent[i][g_label_index])
            g_label = map_dict[g_label_unmapped]["disp_name"] 
            i_labels,i_sub_labels = get_term(result_sent[i][r_label_index])
            results_dict["stats"]["dual_predictions"] += 1 if (len(i_labels) == 2) else 0
            if (strict_check):
                #Pick only one entity from prediction
                i_label = other_tag
                if (g_label != i_labels[0]):
                    failed = True
                    if (i_labels[0] != other_tag and i_labels[0] not in fp_type_list):
                        i_label = misc_tag
                    else:
                        if (i_labels[0] != other_tag):
                            i_label = fp_type_to_disp_map[i_labels[0]]
                else:
                    i_label = i_labels[0]
                if (i_label == other_tag):
                    i_label = map_dict[other_tag]["disp_name"]
                results_dict["entities"][g_label][i_label] += 1
            else:
                #Pick best of both predictions
                found = False
                for j in range(len(i_labels)):
                    if (g_label == i_labels[j] or in_alias_list(map_dict,g_label_unmapped,i_labels[j])):
                        found = True
                        results_dict["entities"][g_label][g_label] += 1
                        break
                if (not found):
                        if (g_label == misc_tag):
                            ret_val = single_term_fp_check(results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index,other_tag,misc_tag,i)
                            failed = True if ret_val else failed
                        else:
                            failed = True
                            if (i_labels[0] in fp_type_list):
                                i_label = fp_type_to_disp_map[i_labels[0]] 
                            else:
                                i_label = map_dict[other_tag]["disp_name"]
                            results_dict["entities"][g_label][i_label] += 1
        else:
            #false positive check. Ground truth is O  if we come here (this is for senteces that have some labels and some O tags
            ret_val = single_term_fp_check(results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index,other_tag,other_tag,i) #sending other_tag twice is not typo. 
            failed = True if ret_val else failed
    return failed

            


        
    
def compute_cf_matrix(results_dict):
    run_total = 0
    for key in results_dict["entity_counts"]:
        run_total += results_dict["entity_counts"][key]
    assert(run_total == results_dict["stats"]["tested_entity_count"])
    f1_score_dict = OrderedDict()
    for key_i in results_dict["entities"]:
        if (key_i == "entity_counts" or key_i == "stats"):
            continue
        f1_score_dict[key_i] = {"precision":0,"recall":0,"f1_score":0,"recall_val": 0,"prec_val":0}
    for key_i in results_dict["entities"]:
        if (key_i == "entity_counts" or key_i == "stats"):
            continue
        total_val = 0
        for key_j in results_dict["entities"][key_i]:
            total_val += results_dict["entities"][key_i][key_j]
            if (key_i == key_j):
                f1_score_dict[key_i]["recall_val"] = results_dict["entities"][key_i][key_j]
        assert(total_val == results_dict["entity_counts"][key_i + "_count"])
        f1_score_dict[key_i]["recall_val_total"] = total_val
        f1_score_dict[key_i]["recall"] =  0 if (total_val == 0) else  round(float(f1_score_dict[key_i]["recall_val"])/total_val,2)


    for key_i in results_dict["entities"]:
        if (key_i == "entity_counts" or key_i == "stats"):
            continue
        total_val = 0
        for key_j in results_dict["entities"]:
            if (key_j == "entity_counts" or key_j == "stats"):
                continue
            for key_k in results_dict["entities"][key_j]:
                if (key_i == key_k):
                    if (key_j == key_i):
                        f1_score_dict[key_i]["prec_val"] += results_dict["entities"][key_j][key_k]
                    total_val += results_dict["entities"][key_j][key_k]
                    break
        f1_score_dict[key_i]["prec_val_total"] = total_val
        f1_score_dict[key_i]["precision"] =  0 if (total_val == 0) else round(float(f1_score_dict[key_i]["prec_val"])/total_val,2)
    
    average_f1_score = 0
    f_count = 0
    for key in f1_score_dict:
        if (float(f1_score_dict[key]["precision"]) + float(f1_score_dict[key]["recall"]) != 0):
            f1_score_dict[key]["f1_score"] = round((2*(float(f1_score_dict[key]["precision"]) * float(f1_score_dict[key]["recall"])))/(float(f1_score_dict[key]["precision"]) + float(f1_score_dict[key]["recall"])),2)
            if (key != "OTHER" and key != "O"):
                average_f1_score  += f1_score_dict[key]["f1_score"]
                f_count += 1
                
                
            
    print("Total tested",results_dict["stats"]["tested_entity_count"])
    results_dict["f1_scores"] = f1_score_dict
    results_dict["average_f1_score"] = round(average_f1_score/f_count,2)
    
def log_failed_empty_prediction(gr_sent,fp,term_index):
    sent = []
    for i in range(len(gr_sent)):
        sent.append(gr_sent[i][term_index])
    sent = ' '.join(sent)
    fp.write(sent + "\n")

def extract(param):
    input_file = cf.read_config(param.config)["input"]
    ground_truth = cf.read_config(param.config)["ground"]
    output_file = cf.read_config(param.config)["output"]
    empty_predictions_file = cf.read_config(param.config)["empty_predictions"]
    resynced_output_file = cf.read_config(param.config)["resynced_output"]
    failed_sentences_file = cf.read_config(param.config)["failed_sentences"]
    passed_sentences_file = cf.read_config(param.config)["passed_sentences"]
    oos_sentences_file = cf.read_config(param.config)["oos_sentences"]
    g_term_index =  cf.read_config(param.config)["term_index"]
    g_label_index =  cf.read_config(param.config)["label_index"]
    entity_mapping =   cf.read_config(param.config)["mapping"]
    fp_type_list =   cf.read_config(param.config)["fp_type_list"]
    fp_subtype_list =   cf.read_config(param.config)["fp_subtype_list"]
    fp_type_to_disp_map =   cf.read_config(param.config)["fp_type_to_disp_map"]
    other_tag = cf.read_config(param.config)["other_tag"]
    misc_tag = cf.read_config(param.config)["misc_tag"]
    ignore_false_positives = param.ignore_others
    r_term_index = 0
    r_label_index = 1
    strict_mode = param.strict
    
    wfp = open((("1p_" if param.strict else "2p_") + output_file.split('/')[-1]),"w")
    gfp = open(ground_truth)
    resynced_fp = open(resynced_output_file,"w")
    failed_fp = open(failed_sentences_file,"w")
    passed_fp = open(passed_sentences_file,"w")
    oos_fp = open(oos_sentences_file,"w")
    empty_predictions_fp = open(empty_predictions_file,"w")
    fp = open(input_file)
    s_count = 0
    full_count = 0
    oos_count = 0
    failed_count = 0
    results_dict,map_dict = construct_cf_matrix(entity_mapping)
    while (True):
        result_sent = get_sentence(fp)
        gr_sent = get_sentence(gfp)
        if (len(gr_sent) == 0 or len(result_sent) == 0):
            if (len(gr_sent) == 0 and len(result_sent) == 0):
                break
            else:
                assert(len(gr_sent) != 0)
                log_failed_empty_prediction(gr_sent,empty_predictions_fp,g_term_index)
                full_count += 1
                oos_count += 1
                continue
        full_count += 1
        #if (full_count == 1748):
        #    pdb.set_trace()
        to_process,gr_sent,result_sent  = reconcile_tokenization_differences(gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index)
        if (to_process):
           s_count += 1
           #print("process_line",s_count) 
           #if (s_count == 20141):
           #    pdb.set_trace()
           assert(len(gr_sent) == len(result_sent))
           output_resynced_results(resynced_fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index)
           failed = eval_sentence(results_dict,map_dict,fp_type_list,fp_subtype_list,fp_type_to_disp_map,gr_sent,result_sent,g_term_index,g_label_index,0,1,other_tag,misc_tag,strict_mode,ignore_false_positives)
           if (failed):
                failed_count += 1
                output_resynced_results(failed_fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index)
           else:
                output_passed_results(passed_fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index)
        else:
           #print("skipped_line",full_count)
           output_oos_sentence(oos_fp,gr_sent,result_sent,g_term_index,g_label_index,r_term_index,r_label_index)
           oos_count += 1
                
            
    assert(full_count == s_count + oos_count) 
    compute_cf_matrix(results_dict) 
    print("Total sentences",full_count)
    print("Processed sentences",s_count)
    print("OOS sentences",oos_count, round((float(oos_count)/full_count)*100,2))
    print("Failed sentences (at least one failure)",failed_count, round((float(failed_count)/full_count)*100,2))
    results_dict["stats"]["total_sentences"] = full_count
    results_dict["stats"]["processed_sentences"] = s_count
    results_dict["stats"]["out_of_sync_sentences"] = oos_count
    results_dict["stats"]["OOS_percent"] = round((float(oos_count)/full_count)*100,2)
    results_dict["stats"]["at_least_one_entity_failed_sentences"] = failed_count
    results_dict["stats"]["at_least_one_entity_failed_percent"] = round((float(failed_count)/full_count)*100,2)
    results_dict["stats"]["dual_predictions_percent"] = round(float(results_dict["stats"]["dual_predictions"])/(float(results_dict["stats"]["tested_entity_count"]))*100,2)
    results_dict["stats"]["others_only_tokens_percent"] = round(float(results_dict["stats"]["others_only_token_count"])/(float(results_dict["stats"]["tested_entity_count"]))*100,2)
    results_dict["stats"]["others_only_sentence_percent"] = round(float(results_dict["stats"]["others_only_sentence_count"])/full_count*100,2)
    print(json.dumps(results_dict,indent=4))
    wfp.write(json.dumps(results_dict,indent=4))
    wfp.close()
    gfp.close()
    oos_fp.close()
    empty_predictions_fp.close()
             


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Eval script of NER results',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-config', action="store", dest="config",default="eval_config.json",help='Default config file for eval')
    parser.add_argument('-strict', dest="strict", action='store_true',help='Do not use both predictions - just the first')
    parser.add_argument('-no-strict', dest="strict", action='store_false',help='Use both predictions')
    parser.add_argument('-ignore_others', dest="ignore_others", action='store_true',help='Ignore false positive check on others only sentences')
    parser.add_argument('-no-ignore_others', dest="ignore_others", action='store_true',help='Do not Ignore false positive check on others only sentences')
    parser.set_defaults(strict=False)
    parser.set_defaults(ignore_others=False)
    results = parser.parse_args()

    extract(results)
