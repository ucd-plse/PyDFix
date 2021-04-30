import sys
import os
import csv


def main(args):
    path = args[2]
    dataset = None
    if len(args) == 5:
        dataset = int(args[4])
    if not dataset or dataset == 1:
        bugswarm_repro_log_dir = 'repro_log_bugswarm'
        bugswarm_total = 2584
        bugswarm_available = len([name for name in os.listdir(os.path.join(path, bugswarm_repro_log_dir)) if os.path.isfile(os.path.join(path, bugswarm_repro_log_dir, name))])
        bugswarm_id = []
        with open(os.path.join(path, 'artifacts_dependency_broken.csv')) as f:
            csv_reader = csv.reader(f)
            next(csv_reader, None)
            for row in csv_reader:
                bugswarm_id.append(row)
        if bugswarm_available == 0:
            print('No reproduced log for BugSwarm found. Please make sure the repro_log_bugswarm contains all reproduced logs')
        else:
            print('Dataset: BugSwarm')
            print('Builds Available: {} Builds Analyzed: {} Builds Indentified: {}'.format(bugswarm_total, bugswarm_available, '{}({})'.format(len(bugswarm_id), len(bugswarm_id)*100/bugswarm_available)))
    if not dataset or dataset == 2:
        bugsinpy_repro_log_dir = 'repro_log_bugsinpy'
        bugsinpy_total = 1002
        bugsinpy_available = len([name for name in os.listdir(os.path.join(path, bugsinpy_repro_log_dir)) if os.path.isfile(os.path.join(path, bugsinpy_repro_log_dir, name))])
        bugsinpy_id = []
        with open(os.path.join(path, 'bugsinpy_artifacts_dependency_broken.csv')) as f:
            csv_reader = csv.reader(f)
            next(csv_reader, None)
            for row in csv_reader:
                bugsinpy_id.append(row)
        if bugsinpy_available == 0:
            print('No reproduced log for BugsInPy found. Please make sure the repro_log_bugsinpy contains all reproduced logs')
        else:
            print('Dataset: BugsInPy')
            print('Builds Available: {} Builds Analyzed: {} Builds Indentified: {}'.format(bugsinpy_total, bugsinpy_available, '{}({})'.format(len(bugsinpy_id), len(bugsinpy_id)*100/bugsinpy_available)))

    if dataset != 1 and dataset != 2:
        print('No such dataset is included in this study')



if __name__ == '__main__':
    # python3 recreate_table4.py
    # -path <path to PyDFix>
    # (optional) -dataset <1 for BugSwarm 2 for BugsInPy
    main(sys.argv)