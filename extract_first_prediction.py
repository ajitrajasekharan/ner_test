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
import pdb

def extract(input_file,output_file):
    wfp = open(output_file,"w")
    with open(input_file) as fp:
        for line in fp:
            line = line.rstrip("\n")
            arr = line.split()
            if (len(arr) > 1):
                p_field = arr[1].split("/")[0].split("[")[0]
                print(arr[0],p_field)
                wfp.write(arr[0] + " " +  p_field + "\n")
            else:
                print(line)
                wfp.write("\n")
    wfp.close()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Conversion utility to extract only the first type in prediction from a columnar format file and output the resultant columnar file  ',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-input', action="store", dest="input",default="ner_output.txt",help='Input file for batch run option')
    parser.add_argument('-output', action="store", dest="output",default="test.tsv",help='Input file for batch run option')
    results = parser.parse_args()

    extract(results.input,results.output)
