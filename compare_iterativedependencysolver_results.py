import sys
from os.path import join
import csv
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils


def main(args):
    path = args[2]
    dataset = args[4]
    orig_file_name = None
    new_file_name = None
    result_file_prefix = None
    header_consts = None
    is_subset_run = False
    if len(args) == 6:
        is_subset_run = True
    if dataset == '1':
        if is_subset_run:
            orig_file_name = 'bugswarm_subset_iterative_solve_results_orig.csv'
        else:
            orig_file_name = 'bugswarm_iterative_solve_results_orig.csv'
        new_file_name = 'iterative_solve_results.csv'
        result_file_prefix = 'bugswarm'
        header_consts = DependencyAnalyzerConstants.COMPARE_BUGSWARM_CSV_SOLVER_RESULTS_HEADERS
    elif dataset == '2':
        if is_subset_run:
            orig_file_name = 'bugsinpy_subset_iterative_solve_results_orig.csv'
        else:
            orig_file_name = 'bugsinpy_iterative_solve_results_orig.csv'
        new_file_name = 'bugsinpy_iterative_solve_results.csv'
        result_file_prefix = 'bugsinpy'
        header_consts = DependencyAnalyzerConstants.COMPARE_BUGSWARM_CSV_SOLVER_RESULTS_HEADERS
    else:
        print('No such dataset exists in this study')
        return
    orig_data = []
    new_data = []
    # read original data
    with open(join(path, 'orig_data', orig_file_name)) as f:
        csv_reader = csv.reader(f)
        next(csv_reader, None)
        for row in csv_reader:
            orig_data.append(row)
    # read new data
    with open(join(path, new_file_name)) as f:
        csv_reader = csv.reader(f)
        next(csv_reader, None)
        for row in csv_reader:
            new_data.append(row)
    diff_in_num_id = len(orig_data) - len(new_data)
    new_found = []
    same_fix_outcome = []
    nofix_to_partial = []
    nofix_to_complete = []
    partial_to_complete = []
    complete_to_partial = []
    complete_to_nofix = []
    partial_to_nofix = []
    orig_data_map = {}
    for row in orig_data:
        orig_data_map[row[0]] = row
    for row in new_data:
        key = row[0]
        if key not in orig_data_map:
            new_found.append(row)
        else:
            orig_row = orig_data_map[key]
            compare_row = []
            compare_row.extend(row)
            compare_row.extend(orig_row[1:])
            if not len(row[1]):
                # no fix
                if len(orig_row[1]):
                    if orig_row[2].strip() == 'No longer recognized as a dependency error' or orig_row[2].strip() == 'Exhausted all options':
                        partial_to_nofix.append(compare_row)
                    else:
                        complete_to_nofix.append(compare_row)
                else:
                    same_fix_outcome.append(compare_row)
            elif row[2].strip() == 'No longer recognized as a dependency error' or row[2].strip() == 'Exhausted all options':
                # partial fix
                if not len(orig_row[1]):
                    nofix_to_partial.append(compare_row)
                elif orig_row[2].strip() == 'No longer recognized as a dependency error' or orig_row[2].strip() == 'Exhausted all options':
                    same_fix_outcome.append(compare_row)
                else:
                    complete_to_partial.append(compare_row)
            else:
                # complete fix
                if not len(orig_row[1]):
                    nofix_to_complete.append(compare_row)
                elif orig_row[2].strip() == 'No longer recognized as a dependency error' or orig_row[2].strip() == 'Exhausted all options':
                    partial_to_complete.append(compare_row)
                else:
                    same_fix_outcome.append(compare_row)
    if diff_in_num_id > 0:
        print('Decrease in number of fixes attempted: {}'.format(abs(diff_in_num_id)))
    elif diff_in_num_id < 0:
        print('Increase in number of fixes attempted: {}'.format(abs(diff_in_num_id)))
    else:
        print('Same number of fixes attempted')
    print('Same fix outcome count: {}'.format(len(same_fix_outcome)))
    print('========Improvements=======')
    print('No fix to partial fix: {}'.format(len(nofix_to_partial)))
    print('No fix to complete fix: {}'.format(len(nofix_to_complete)))
    print('Partial fix to complete fix: {}'.format(len(partial_to_complete)))
    print('========Deterioration=======')
    print('Complete fix to no fix: {}'.format(len(complete_to_nofix)))
    print('Complete fix to partial fix: {}'.format(len(complete_to_partial)))
    print('Partial fix to no fix: {}'.format(len(partial_to_nofix)))
    DependencyAnalyzerUtils.write_to_csv(same_fix_outcome,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_same_fix_outcome.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(nofix_to_partial,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_nofix_to_partial.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(nofix_to_complete,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_nofix_to_complete.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(partial_to_complete,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_partial_to_complete.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(complete_to_nofix,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_complete_to_nofix.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(complete_to_partial,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_complete_to_partial.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(partial_to_nofix,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_partial_to_nofix.csv'.format(result_file_prefix))


if __name__ == '__main__':
    # python3 compare_iterativedependencysolver_results.py
    # -path <path to PyDFix>
    # -dataset <1 for BugSwarm 2 for BugsInPy>
    # (optional) -subsetrun
    main(sys.argv)
