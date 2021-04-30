import sys
from os.path import join
import csv
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils


def main(args):
    path = args[2]
    dataset = args[4]
    is_subset_run = False
    if len(args) == 6:
        is_subset_run = True
    orig_file_name = None
    new_file_name = None
    result_file_prefix = None
    if dataset == '1':
        if not is_subset_run:
            orig_file_name = 'bugswarm_artifacts_dependency_broken_orig.csv'
        else:
            orig_file_name = 'bugswarm_subset_artifacts_dependency_broken_orig.csv'
        new_file_name = 'artifacts_dependency_broken.csv'
        result_file_prefix = 'bugswarm'
    elif dataset == '2':
        if not is_subset_run:
            orig_file_name = 'bugsinpy_artifacts_dependency_broken_orig.csv'
        else:
            orig_file_name = 'bugsinpy_subset_artifacts_dependency_broken_orig.csv'
        new_file_name = 'bugsinpy_artifacts_dependency_broken.csv'
        result_file_prefix = 'bugsinpy'
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
    prev_skipped = []
    common_diff_error = []
    orig_data_map = {}
    for row in orig_data:
        orig_data_map[row[0]] = row
    for row in new_data:
        key = row[0]
        if key not in orig_data_map:
            new_found.append(row)
            continue
        if key in orig_data_map:
            orig_row = orig_data_map[key]
            if orig_row[1] != row[1]:
                contrast_row = row
                contrast_row.append(orig_row[1])
                contrast_row.append(orig_row[2])
                common_diff_error.append(contrast_row)
            del orig_data_map[key]
            continue
    prev_skipped = list(orig_data_map.values())
    if diff_in_num_id > 0:
        print('Decrease in number identified: {}'.format(abs(diff_in_num_id)))
    elif diff_in_num_id < 0:
        print('Increase in number identified: {}'.format(abs(diff_in_num_id)))
    else:
        print('Number identified: No Change')
    print('New identified: {}'.format(len(new_found)))
    print('Not identified from previously identified: {}'.format(len(prev_skipped)))
    print('Error identified changed: {}'.format(len(common_diff_error)))
    DependencyAnalyzerUtils.write_to_csv(new_found,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_new_found.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(prev_skipped,
                                         DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_prev_skipped.csv'.format(result_file_prefix))
    DependencyAnalyzerUtils.write_to_csv(common_diff_error,
                                         DependencyAnalyzerConstants.COMPARE_ARTIFACTS_BROKEN_HEADERS,
                                         '{}_compare_common_diff_error.csv'.format(result_file_prefix))



if __name__ == '__main__':
    # python3 compare_logerroranalyzer_results.py
    # -path <path to PyDFix>
    # -dataset <1 for BugSwarm 2 for BugsInPy>
    # (optional) -subsetrun
    main(sys.argv)
