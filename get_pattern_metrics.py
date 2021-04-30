import sys
import csv
import re
from os.path import join
from error_type import ErrorType
from dependency_analyzer_const import DependencyAnalyzerConstants

def main(args):
    path = args[2]
    filename = args[4]
    content = []
    total_err_type_dict = {}
    with open(join(path, filename), 'r') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            content.append(row)
    for row in content:
        err_type_dict = {}
        error_id_list = row[1].split(DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
        for err in error_id_list:
            for err_type in ErrorType:
                match_obj = re.search(
                    DependencyAnalyzerConstants.INEXACT_PATTERN_LIST[err_type], err, re.M)
                if match_obj:
                    exact_match = re.search(
                        DependencyAnalyzerConstants.ERROR_PATTERN_LIST[err_type], err, re.M)
                    if exact_match and err_type not in err_type_dict:
                        err_type_dict[err_type] = True
        for err in err_type_dict:
            if err in total_err_type_dict:
                total_err_type_dict[err] = total_err_type_dict[err] + 1
            else:
                total_err_type_dict[err] = 1
    print(total_err_type_dict)


if __name__ == '__main__':
    # python3 get_pattern_metrics.py 
    # -path <path to file>
    # -filename <filename>
    main(sys.argv)