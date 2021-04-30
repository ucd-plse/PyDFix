import csv
import json
import sys


def main(args):
    orig_metrics = []
    with open('orig_log_metrics.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            orig_metrics.append(row)
    all_patches = []
    with open('iterative_solve_results.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            all_patches.append(row)
    op = []
    all_patches_dict = {}
    orig_metrics_dict = {}
    for patch in all_patches:
        if len(patch[1].strip()) == 0:
            continue
        filnm = patch[0].split('.')[0] + '_' + patch[0].split('.')[1]
        p = [x.split('==')[0] for x in patch[1].split()]
        outcome = patch[2]
        all_patches_dict[filnm] = {'patches': p, 'outcome': outcome}
    for metric in orig_metrics:
        filnm = metric[0].strip() + '_' + metric[1].strip()
        m = json.loads(metric[-1])
        orig_metrics_dict[filnm] = m
    skip_count = 0
    pinned_patches = {'all':0, 'complete':0, 'partial':0, 'max': 0, 'average':0}
    constr_patches = {'all':0, 'complete':0, 'partial':0, 'max': 0, 'average':0}
    unconstr_patches = {'all':0, 'complete':0, 'partial':0, 'max': 0, 'average':0}
    proj_patches = {'all':0, 'complete':0, 'partial':0, 'max': 0, 'average':0}
    tran_patches = {'all':0, 'complete':0, 'partial':0, 'max': 0, 'average':0}
    overall_max = 0
    for f in all_patches_dict:
        patch = all_patches_dict[f]['patches']
        outcome = all_patches_dict[f]['outcome']
        metric = orig_metrics_dict[f]
        if isinstance(metric, int):
            skip_count += 1
            continue
        if len(patch) > overall_max:
            overall_max = len(patch)
        tran = 0
        proj = 0
        new = 0
        pin = 0
        unconstr = 0
        constr = 0
        for p in patch:
            found = False
            for m in metric:
                if m['_name'] == p:
                    found = True
                    if m['_is_transitive']:
                        tran += 1
                    else:
                        proj += 1
                    if m['_version_pinned']:
                        pin += 1
                    elif m['_version_constraints']:
                        constr += 1
                    else:
                        unconstr += 1
        pinned_patches['all'] += pin
        constr_patches['all'] += constr
        unconstr_patches['all'] += unconstr
        proj_patches['all'] += proj
        tran_patches['all'] += tran
        if outcome.startswith('Successful') or outcome.startswith('Restored'):
            pinned_patches['complete'] += pin
            constr_patches['complete'] += constr
            unconstr_patches['complete'] += unconstr
            proj_patches['complete'] += proj
            tran_patches['complete'] += tran
        elif outcome.startswith('No longer') or outcome.startswith('Exhausted'):
            pinned_patches['partial'] += pin
            constr_patches['partial'] += constr
            unconstr_patches['partial'] += unconstr
            proj_patches['partial'] += proj
            tran_patches['partial'] += tran
        if pin > pinned_patches['max']:
            pinned_patches['max'] = pin
        if constr > constr_patches['max']:
            constr_patches['max'] = constr
        if unconstr > unconstr_patches['max']:
            unconstr_patches['max'] = unconstr
        if proj > proj_patches['max']:
            proj_patches['max'] = proj
        if tran > tran_patches['max']:
            tran_patches['max'] = tran
        op.append([f, tran, proj,  pin, constr, unconstr])
    print(skip_count)
    with open('patch_metrics.csv', 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Artifact Name', 'Transitive', 'Project', 'Pinned', 'Constrained', 'Unconstrained'])
        for row in op:
            writer.writerow(row)
    total_patches = proj_patches['all'] + tran_patches['all']
    total_complete_patches = proj_patches['complete'] + tran_patches['complete']
    total_partial_patches = proj_patches['partial'] + tran_patches['partial']
    total_partial_patches = proj_patches['partial'] + tran_patches['partial']
    print('==========**** BugSwarm Patch Metrics ****==========')
    print('Pinned Dependencies:')
    print('All:{} Complete:{} Partial:{} Max:{} Average:{}'.format(pinned_patches['all'], pinned_patches['complete'], pinned_patches['partial'], pinned_patches['max'], pinned_patches['all']/len(all_patches_dict)))
    print('====================================================')
    print('Constrained Dependencies:')
    print('All:{} Complete:{} Partial:{} Max:{} Average:{}'.format(constr_patches['all'], constr_patches['complete'], constr_patches['partial'], constr_patches['max'], constr_patches['all']/len(all_patches_dict)))
    print('====================================================')
    print('Unconstrained Dependencies:')
    print('All:{} Complete:{} Partial:{} Max:{} Average:{}'.format(unconstr_patches['all'], unconstr_patches['complete'], unconstr_patches['partial'], unconstr_patches['max'], unconstr_patches['all']/len(all_patches_dict)))
    print('====================================================')
    print('Project Dependencies:')
    print('All:{} Complete:{} Partial:{} Max:{} Average:{}'.format(proj_patches['all'], proj_patches['complete'], proj_patches['partial'], proj_patches['max'], proj_patches['all']/len(all_patches_dict)))
    print('====================================================')
    print('Transitive Dependencies:')
    print('All:{} Complete:{} Partial:{} Max:{} Average:{}'.format(tran_patches['all'], tran_patches['complete'], tran_patches['partial'], tran_patches['max'], tran_patches['all']/len(all_patches_dict)))
    print('====================================================')
    print('Overall Dependencies:')
    print('All:{} Complete:{} Partial:{} Max:{} Average:{}'.format(total_patches, total_complete_patches, total_partial_patches, overall_max, total_patches/len(all_patches_dict)))
    print('==========**** END OF OUTPUT ****==========')

if __name__ == '__main__':
    # python3 gather_metrics_from_orig_logs.py 
    # -path <path to artifacts.json>
    main(sys.argv)
