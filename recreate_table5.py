import sys
import os
import csv


def main(args):
    path = args[2]
    dataset = None
    if len(args) == 5:
        dataset = int(args[4])
    if not dataset or dataset == 1:
        bugswarm_fixes = []
        bugswarm_id = []
        bugswarm_full_fix = 0
        bugswarm_partial_fix = 0

        with open(os.path.join(path, 'artifacts_dependency_broken.csv')) as f:
            csv_reader = csv.reader(f)
            next(csv_reader, None)
            for row in csv_reader:
                bugswarm_id.append(row)

        with open(os.path.join(path, 'iterative_solve_results.csv')) as f:
            csv_reader = csv.reader(f)
            next(csv_reader, None)
            for row in csv_reader:
                bugswarm_fixes.append(row)

        for row in bugswarm_fixes:
            if len(row[1]) == 0:
                continue
            if row[2].startswith('Successful') or row[2].startswith('Restored'):
                bugswarm_full_fix += 1
            elif row[2].startswith('No longer') or row[2].startswith('Exhausted'):
                bugswarm_partial_fix += 1

        print('Dataset: BugSwarm')
        print('Builds Identified: {} Complete Fix: {} Partial Fix: {}'.format(len(bugswarm_id), '{}({})'.format(bugswarm_full_fix, bugswarm_full_fix*100/len(bugswarm_id)), '{}({})'.format(bugswarm_partial_fix, bugswarm_partial_fix*100/len(bugswarm_id))))
    if not dataset or dataset == 2:
        bugsinpy_fixes = []
        bugsinpy_id = []
        bugsinpy_full_fix = 0
        bugsinpy_partial_fix = 0

        with open(os.path.join(path, 'bugsinpy_artifacts_dependency_broken.csv')) as f:
            csv_reader = csv.reader(f)
            next(csv_reader, None)
            for row in csv_reader:
                bugsinpy_id.append(row)
        with open(os.path.join(path, 'bugsinpy_iterative_solve_results.csv')) as f:
            csv_reader = csv.reader(f)
            next(csv_reader, None)
            for row in csv_reader:
                bugsinpy_fixes.append(row)

        for row in bugsinpy_fixes:
            if len(row[1]) == 0:
                continue
            if row[2].startswith('Successful') or row[2].startswith('Restored'):
                bugsinpy_full_fix += 1
            elif row[2].startswith('No longer') or row[2].startswith('Exhausted'):
                bugsinpy_partial_fix += 1
        print('Dataset: BugsInPy')
        print('Builds Identified: {} Complete Fix: {} Partial Fix: {}'.format(len(bugsinpy_id), '{}({})'.format(bugsinpy_full_fix, bugsinpy_full_fix*100/len(bugsinpy_id)), '{}({})'.format(bugsinpy_partial_fix, bugsinpy_partial_fix*100/len(bugsinpy_id))))


if __name__ == '__main__':
    # python3 recreate_table5.py
    # -path <path to PyDFix>
    # (optional) -dataset <1 for BugSwarm 2 for BugsInPy>
    main(sys.argv)
