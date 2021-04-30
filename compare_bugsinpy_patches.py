import sys
import csv
import codecs
from os.path import isfile, join


def main(args):
    path = args[2]
    component_path = args[4]
    final_op = []
    content = []
    with open(join(path, 'bugsinpy_iterative_solve_results.csv'), 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            content.append(row)
    for row in content:
        encoding_type = 'utf-16'
        proj_bug_ver = row[0]
        computed_patches = row[1]
        # artifact id , maintainer's patch, computed patch, fix outcome, not
        # included from maintainer patch, new included not in maintainer patch,
        # common patches
        curr_op = [proj_bug_ver]
        proj = proj_bug_ver.split('_')[0]
        bug = proj_bug_ver.split('_')[1]
        if not isfile(join(component_path, 'projects', proj, 'bugs', bug, 'requirements.txt')):
            curr_op.extend(['', computed_patches, row[2], '', computed_patches, ''])
            final_op.append(curr_op)
            continue
        req_file_contents = []
        fo = codecs.open(join(component_path, 'projects', proj, 'bugs', bug, 'requirements.txt'), 'rb')
        req_file_contents = fo.read()
        fo.close()
        try:
            req_file_contents = req_file_contents.decode('utf-8')
        except Exception as e:
            try:
                req_file_contents = req_file_contents.decode('utf-16')
                encoding_type = 'utf-8'
            except Exception as e:
                print(e)
                continue
        req_file_contents = req_file_contents.split('\n')
        req_file_contents = [x.replace('\r', '') for x in req_file_contents]
        req_file_dict = {}
        computed_dict = {}
        for req_row in req_file_contents:
            if '==' not in req_row:
                continue
            pkg = req_row.split('==')[0]
            version = req_row.split('==')[1]
            req_file_dict[pkg] = version
        for computed_patch in computed_patches.split():
            pkg = computed_patch.split('==')[0]
            version = computed_patch.split('==')[1]
            computed_dict[pkg] = version
        common = {}
        not_in_computed = {}
        not_in_orig = {}
        for pkg in computed_dict:
            if pkg in req_file_dict:
                common[pkg] = computed_dict[pkg]
                del req_file_dict[pkg]
                continue
            else:
                not_in_orig[pkg] = computed_dict[pkg]
        not_in_computed = req_file_dict
        str_common = ''
        str_not_in_orig = ''
        str_not_in_computed = ''
        for c in common:
            str_common += c + '==' + common[c] + ' '
        for n in not_in_computed:
            str_not_in_computed += n + '==' + not_in_computed[n] + ' '
        for n in not_in_orig:
            str_not_in_orig += n + '==' + not_in_orig[n] + ' '
        curr_op.extend([' '.join(req_file_contents), computed_patches, row[2], str_not_in_computed, str_not_in_orig, str_common])
        final_op.append(curr_op)
    with open('compare_bugsinpy_patches.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Artifact ID', 'Maintainers\' Patch', 'Computed Patch', 'Fix Outcome', 'Not in Computed', 'Not in Maintainers\'', 'Common'])
        for row in final_op:
            writer.writerow(row)


if __name__ == '__main__':
    # python3 compare_bugsinpy_patches.py
    # -path <path to bugsinpy_iterative_solve_results.csv>
    # -component <path to BugsInPy component>
    main(sys.argv)

