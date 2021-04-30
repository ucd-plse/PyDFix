import sys
import csv
from os.path import isfile, join
from os import listdir
import traceback
from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.common.log_downloader import download_log
from dependency_analyzer_utils import DependencyAnalyzerUtils
from dependency_analyzer_const import DependencyAnalyzerConstants


def main(args):
    op = []
    content = read_csv_content('run_analyzer.csv')
    log_path = args[2]
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo mkdir temp_logs')
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo chmod -R 777 temp_logs')
    artifact_dict = DependencyAnalyzerUtils.get_artifact_dict('/home/sumukher/bugswarm-dev/dependency-solver/scripts')
    for row in content:
        log_file_nm = row[0]
        prev_reason = row[1]
        art_name = log_file_nm.split('.')[0]
        f_or_p = log_file_nm.split('.')[1]
        try:
            run_dirs = listdir(join(log_path, art_name, f_or_p))
            run_dirs.reverse()
            target_dir = run_dirs[0]
            if not isfile(join(log_path, art_name, f_or_p, target_dir, 'log-output.log')) and len(run_dirs) > 1 and run_dirs[1].startswith('run-'):
                target_dir = run_dirs[1]
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo cp {} temp_logs/{}'.format(join(log_path, art_name, f_or_p, target_dir, 'log-output.log'), log_file_nm))
            job_id = artifact_dict[art_name]['{}_job'.format(f_or_p)]['job_id']
            print(job_id)
            original_log_name = '{}.{}.orig.log'.format(art_name, f_or_p)
            downloaded = download_log(job_id, join('temp_logs', original_log_name))
            if not downloaded:
                repo_name = artifact_dict[art_name]['repo']
                if not get_log_from_image(art_name, f_or_p, repo_name):
                    op.append([log_file_nm, prev_reason, 'Failed to get original log'])
                    continue
            repro_log_path = join('temp_logs', log_file_nm)
            orig_log_path = join('temp_logs', original_log_name)
            analyzer_results = Analyzer.compare_single_log(repro_log_path, orig_log_path, job_id)
            op.append([log_file_nm, prev_reason, analyzer_results])
            break
        except Exception as e:
            print(e)
            traceback.print_exc()
            op.append([log_file_nm, prev_reason, 'Analyzer Errored'])
    with open('analyzer_run_results.csv', 'w') as f:
        writer = csv.writer(f)
        for row in op:
            writer.writerow(row)


def get_log_from_image(art_name, f_or_p, repo_name):
    docker_container_cmd = DependencyAnalyzerConstants.DOCKER_RUN_IMAGE_CMD.format(art_name)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_container_cmd)
    if not ok:
        print('Failed to run Docker container')
        return False
    get_container_id_cmd = DependencyAnalyzerConstants.DOCKER_GET_CONTAINER_ID_CMD
    _, container_id, _, _ = DependencyAnalyzerUtils._run_command(get_container_id_cmd)
    if not container_id:
        print('Failed to run Docker container')
        return False
    docker_cp_src_code = 'docker cp {}:/home/travis/build/{}/{}/{} {}'.format(container_id, f_or_p, repo_name, 'home/sumukher/bugswarm-dev/dependency-solver/scripts/temp_logs')
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_cp_src_code)
    if not ok:
        print(stderr)
        return False
    return True


def read_csv_content(csv_name):
    content = []
    with open(csv_name, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            content.append(row)
    return content


if __name__ == '__main__':
    # python3 run_analyzer.py 
    # -logpath <path to logs>
    main(sys.argv)