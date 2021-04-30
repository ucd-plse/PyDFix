#!/usr/bin/python3

from http import HTTPStatus
from os.path import isfile, join, isdir, expanduser
import os
import csv
import traceback
import requests
import time
import json
import sys
from multiprocessing import Pool, cpu_count
from functools import partial
from build_outcome_type import BuildOutcomeType
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from solver_utils import SolverUtils
from final_outcome import FinalOutcome
from travis_yml_generator import TravisYMLGenerator


""" Implementation of IterativeDependencySolver for BugSwarm """


def main(args):
    overall_start_time = time.time()
    input_files_path = args[2]
    orig_log_files_path = args[4]
    component_path = args[6]
    intermediate_path = args[8]
    fix_file_contents = get_log_analyzer_results(input_files_path)
    change_component_permission(component_path)
    with Pool(cpu_count()) as pool:
        results = pool.map(partial(process_each_artifact_dependency_solve,
                                   component_path=component_path,
                                   intermediate_path=intermediate_path,
                                   orig_log_files_path=orig_log_files_path), fix_file_contents)
    results = [line[0] for line in results]
    DependencyAnalyzerUtils.write_to_csv(results, DependencyAnalyzerConstants.BUGSINPY_CSV_SOLVER_RESULTS_HEADERS, 'bugsinpy_iterative_solve_results.csv')
    partial_fix = 0
    complete_fix = 0
    for row in results:
        if row[2] in [FinalOutcome.SUCCESS_FIXED_BUILD, FinalOutcome.SUCCESS_RESTORED_TO_ORIGINAL_STATUS, FinalOutcome.SUCCESS_RESTORED_TO_ORIGINAL_ERROR] and len(row[1]):
            complete_fix += 1
        elif row[2] in [FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS, FinalOutcome.SUCCESS_NO_LONGER_DEPENDENCY_ERROR, FinalOutcome.PARTIAL_NO_POSSIBLE_CANDIDATES] and len(row[1]):
            partial_fix += 1
    overall_end_time = time.time()
    print('==========**** IterativeDependencySolver FINAL OUTPUT ****==========')
    if len(results) == 0:
        print('No artifacts to solve for')
    else:
        print('Number of builds identified: {}'.format(len(results)))
        print('Complete Fixes: {}({})'.format(complete_fix, complete_fix*100/len(results)))
        print('Partial Fixes: {}({})'.format(partial_fix,partial_fix*100/len(results)))
        print('No Fixes: {}({})'.format(len(results) - (complete_fix + partial_fix), (len(results) - (complete_fix + partial_fix))*100/len(results)))
        print('Total Runtime: {} minutes'.format((overall_end_time - overall_start_time)/60))
    print('==========**** END OF OUTPUT ****==========')


def change_component_permission(component_path):
    """ Change permission for component directory """
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(component_path))


def create_art_dir(intermediate_path, repo_name, bug_id, version):
    """ Create directory to store intermediate files for an artifact """
    if not isdir(join(intermediate_path, repo_name)):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.SUDO_MKDIR.format(join(intermediate_path, repo_name)))
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(intermediate_path, repo_name)))
    if not isdir(join(intermediate_path, repo_name, str(bug_id))):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.SUDO_MKDIR.format(join(intermediate_path, repo_name, str(bug_id))))
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(intermediate_path, repo_name, str(bug_id))))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        DependencyAnalyzerConstants.SUDO_MKDIR.format(join(intermediate_path, repo_name, str(bug_id), str(version))))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(intermediate_path, repo_name, str(bug_id), str(version))))


def process_each_artifact_dependency_solve(fix_file_row, component_path, intermediate_path, orig_log_files_path):
    """ Solve a build """
    final_output = []
    start_time = time.time()
    accepted_patch_str = DependencyAnalyzerConstants.CHAR_EMPTY
    log_output_content = []
    clone_dir = None
    output_log_path = None
    log_file_name = fix_file_row[0].strip()
    repo_name, bug_id, version = get_bug_details(log_file_name)
    final_iter_count = 0
    try:
        solve_result = None
        cleanup(component_path)
        print(log_file_name)
        if not repo_name:
            log_output_content.append(
                FinalOutcome.FAILED_INFO_EXTRACTION_FROM_LOG_FILENM)
            solve_result = FinalOutcome.FAILED_INFO_EXTRACTION_FROM_LOG_FILENM
            cleanup(component_path)
            final_output.append(
                [log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, time.time() - start_time, final_iter_count])
            return final_output
        cloned_repo_dir = setup_bug_repo(
            component_path, repo_name, bug_id, version)
        if not cloned_repo_dir:
            log_output_content.append(FinalOutcome.FAILED_SOURCE_CODE_CLONE)
            solve_result = FinalOutcome.FAILED_SOURCE_CODE_CLONE
            cleanup(component_path)
            final_output.append(
                [log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, time.time() - start_time, final_iter_count])
            return final_output
        clone_dir = cloned_repo_dir
        if not copy_build_script(component_path, cloned_repo_dir, repo_name, bug_id, version):
            log_output_content.append(FinalOutcome.FAILED_BUILD_SCRIPT_COPY)
            solve_result = FinalOutcome.FAILED_BUILD_SCRIPT_COPY
            cleanup(component_path, None, None, clone_dir)
            final_output.append(
                [log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, time.time() - start_time, final_iter_count])
            return final_output
        commit_date = get_commit_date(
            component_path, repo_name, bug_id, version)
        if not commit_date:
            log_output_content.append(FinalOutcome.FAILED_GET_COMMIT_DATE)
            solve_result = FinalOutcome.FAILED_GET_COMMIT_DATE
            cleanup(component_path, None, None, clone_dir)
            final_output.append(
                [log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, time.time() - start_time, final_iter_count])
            return final_output
        curr_errors = fix_file_row[1].split(
            DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
        run_solver = True
        dep_files = fix_file_row[3].strip()
        possible_candidates = json.loads(fix_file_row[2])
        curr_patch_str = DependencyAnalyzerConstants.CHAR_EMPTY
        accepted_patch_str = DependencyAnalyzerConstants.CHAR_EMPTY
        iter_count = -1
        create_art_dir(intermediate_path, repo_name, bug_id, version)
        patches, log_output_content = SolverUtils.generate_patch_combos(
            possible_candidates, commit_date, repo_name, log_output_content, cloned_repo_dir, dep_files)
        while (run_solver):
            iter_count += 1
            final_iter_count += 1
            output_log_path = join(intermediate_path, repo_name, str(bug_id), str(
                version), DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))
            create_run_dir(iter_count, join(intermediate_path,
                                            repo_name, str(bug_id), str(version)))
            found_new_patch = False
            curr_patch_str = accepted_patch_str
            with open(join(output_log_path, DependencyAnalyzerConstants.PATCH_COMBO_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_PLUS_MODE) as f:
                f.write(json.dumps(patches))
            for patch in patches:
                exists_in_accepted = False
                for line in accepted_patch_str.split(DependencyAnalyzerConstants.CHAR_NEW_LINE):
                    if line.strip().startswith(patch[DependencyAnalyzerConstants.NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS):
                        exists_in_accepted = True
                        break
                if exists_in_accepted:
                    continue
                if patch[DependencyAnalyzerConstants.INCLUDED_KEY] or patch[DependencyAnalyzerConstants.APPLIED_KEY]:
                    continue
                if len(patch[DependencyAnalyzerConstants.NAME_KEY]) == 0:
                    curr_patch_str = accepted_patch_str + \
                        patch[DependencyAnalyzerConstants.NAME_KEY] + \
                        DependencyAnalyzerConstants.CHAR_NEW_LINE
                else:
                    curr_patch_str = accepted_patch_str + patch[DependencyAnalyzerConstants.NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS + \
                        patch[DependencyAnalyzerConstants.VERSION_KEY] + \
                        DependencyAnalyzerConstants.CHAR_NEW_LINE
                patch[DependencyAnalyzerConstants.APPLIED_KEY] = True
                found_new_patch = True
                break
            if not found_new_patch:
                log_output_content.append(
                    FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS)
                solve_result = FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS
                cleanup(component_path, output_log_path,
                        log_output_content, cloned_repo_dir)
                break
            with open(join(cloned_repo_dir, DependencyAnalyzerConstants.PATCH_DEPENDENCY_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_PLUS_MODE) as f:
                f.write(curr_patch_str)
            with open(join(output_log_path, DependencyAnalyzerConstants.PATCH_DEPENDENCY_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_MODE) as f:
                f.write(curr_patch_str)
            python_ver = get_value_from_info_file(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, repo_name, DependencyAnalyzerConstants.BUGS_DIR,
                                                       bug_id, DependencyAnalyzerConstants.BUG_INFO_FILENM), DependencyAnalyzerConstants.INFO_PYTHON_VERSION)
            build_outcome, log_output_content = execute_patch_changes(
                cloned_repo_dir, curr_errors, log_output_content, output_log_path, repo_name, bug_id, version, iter_count, python_ver)
            if not build_outcome:
                cleanup(component_path, output_log_path,
                        log_output_content, cloned_repo_dir)
                log_output_content.append(FinalOutcome.FAILED_NO_BUILD_OUTCOME)
                solve_result = FinalOutcome.FAILED_NO_BUILD_OUTCOME
                break
            if build_outcome == BuildOutcomeType.BUILD_SUCCESSFUL:
                log_output_content.append(FinalOutcome.SUCCESS_FIXED_BUILD)
                accepted_patch_str = curr_patch_str
                cleanup(component_path, output_log_path,
                        log_output_content, cloned_repo_dir)
                solve_result = FinalOutcome.SUCCESS_FIXED_BUILD
                break
            else:
                new_errors, candidates_found, new_dep_files, log_output_content = run_log_analyzer(
                    fix_file_row[0], output_log_path, log_output_content, orig_log_files_path, component_path)
                if not candidates_found:
                    if not new_errors:
                        log_output_content.append(
                            FinalOutcome.SUCCESS_NO_LONGER_DEPENDENCY_ERROR)
                        solve_result = FinalOutcome.SUCCESS_NO_LONGER_DEPENDENCY_ERROR
                    else:
                        log_output_content.append(
                            FinalOutcome.PARTIAL_NO_POSSIBLE_CANDIDATES)
                        solve_result = FinalOutcome.PARTIAL_NO_POSSIBLE_CANDIDATES
                    accepted_patch_str = curr_patch_str
                    cleanup(component_path, output_log_path,
                            log_output_content, cloned_repo_dir)
                    break
                new_candidates_found = False
                last_added_patch_caused_error = False
                if len(new_errors):
                    most_probable_candidate = candidates_found[0]
                    last_added_patch = curr_patch_str.strip(DependencyAnalyzerConstants.CHAR_NEW_LINE).split(
                        DependencyAnalyzerConstants.CHAR_NEW_LINE)[-1]
                    if not last_added_patch_caused_error and last_added_patch.startswith(most_probable_candidate[DependencyAnalyzerConstants.CANDIDATE_NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS):
                        #if not most_probable_candidate['_is_pinned'] and not not most_probable_candidate['_version_pinned']:
                        last_added_patch_caused_error = True
                    for candidate in candidates_found:
                        is_new_candidate = True
                        for prev_candidate in possible_candidates:
                            if prev_candidate[DependencyAnalyzerConstants.CANDIDATE_NAME_KEY] == candidate[DependencyAnalyzerConstants.CANDIDATE_NAME_KEY] and prev_candidate[DependencyAnalyzerConstants.CANDIDATE_VERSION_CONSTRAINT_KEY] == candidate[DependencyAnalyzerConstants.CANDIDATE_VERSION_CONSTRAINT_KEY]:
                                # check if pinned version satisfies new constraints
                                is_new_candidate = False
                                break
                        if is_new_candidate:
                            new_candidates_found = True
                            break
                if build_outcome == BuildOutcomeType.NEW_ERROR and last_added_patch_caused_error:
                    if new_candidates_found:
                        curr_errors = new_errors.split(
                            DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
                        patches, log_output_content = SolverUtils.generate_patch_combos(
                            candidates_found, commit_date, repo_name, log_output_content, cloned_repo_dir, new_dep_files)
                    log_output_content.append(
                        'Last added patch caused new error...discarding')
                elif build_outcome == BuildOutcomeType.NEW_ERROR or \
                        (build_outcome == BuildOutcomeType.SAME_ERROR and new_candidates_found):
                    log_output_content.append(
                        'Build error changed or new candidates found')
                    accepted_patch_str = curr_patch_str
                    curr_errors = new_errors.split(
                        DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
                    patches, log_output_content = SolverUtils.generate_patch_combos(
                        candidates_found, commit_date, repo_name, log_output_content, cloned_repo_dir, new_dep_files)
                    possible_candidates = candidates_found
                else:
                    log_output_content.append(
                        'Reject current incremental patch as it did not change error')
    except Exception as e:
        traceback.print_exc()
        print(log_output_content)
        solve_result = FinalOutcome.FAILED_ERROR.format(e)
    end_time = time.time()
    final_output.append([log_file_name, accepted_patch_str.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE,
                                                                   DependencyAnalyzerConstants.CHAR_SPACE), solve_result, (end_time - start_time), final_iter_count])
    log_output_content.append(accepted_patch_str)
    with open(join(intermediate_path, repo_name, str(bug_id), str(version), DependencyAnalyzerConstants.OUTPUT_LOG), DependencyAnalyzerConstants.FILE_WRITE_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        f.write(DependencyAnalyzerConstants.CHAR_NEW_LINE.join(log_output_content))
    cleanup(component_path, output_log_path, log_output_content, clone_dir)
    return final_output


def run_log_analyzer(log_file_nm, output_log_path, log_output_content, orig_log_files_path, component_path):
    """ Run log analyzer to check if a dependency issue still exists, if it does what are the errors and what are the possible candidates """
    if not isdir(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE), 'bugsinpy_intermediate_log')):
        mkdir_log_path_cmd = DependencyAnalyzerConstants.CREATE_DIR_CMD.format(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                               'bugsinpy_intermediate_log')
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            mkdir_log_path_cmd)
        if not ok:
            log_output_content.append(stderr)
            log_output_content.append(
                'Failed to create intermediate log folder')
            return None, None, None, log_output_content
    change_per_cmd = DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                                   'bugsinpy_intermediate_log'))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        change_per_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to change permission')
    cp_log_cmd = DependencyAnalyzerConstants.COPY_FILE_CMD.format(join(output_log_path, log_file_nm),
                                                                  join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                       'bugsinpy_intermediate_log', log_file_nm))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_log_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to copy new log')
        return None, None, None, log_output_content
    analyzer_cmd = DependencyAnalyzerConstants.BUGSINPY_RUN_LOG_ANALYZER.format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                                     'bugsinpy_intermediate_log'), orig_log_files_path, component_path,log_file_nm)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(analyzer_cmd)
    if not ok:
        print(stderr)
        log_output_content.append('Failed to run analyzer')
        return None, None, None, log_output_content
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('cp {} {}'.format('bugsinpy_artifacts_dependency_broken_' + log_file_nm + DependencyAnalyzerConstants.CSV_FILE_EXT,
                                                                                   output_log_path))
    if not ok:
        log_output_content.append('Failed to copy analyzer output')
    errors = None
    candidates = None
    files = None
    found_data = False
    with open('bugsinpy_artifacts_dependency_broken_' + log_file_nm + DependencyAnalyzerConstants.CSV_FILE_EXT, DependencyAnalyzerConstants.FILE_READ_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            errors = row[1]
            candidates = json.loads(row[2])
            files = row[3]
            found_data = True
    if isfile('bugsinpy_artifacts_dependency_broken_' + log_file_nm + DependencyAnalyzerConstants.CSV_FILE_EXT):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_RM_CMD.format(
            'bugsinpy_artifacts_dependency_broken_' + log_file_nm + DependencyAnalyzerConstants.CSV_FILE_EXT))
    if found_data:
        return errors, candidates, files, log_output_content
    return None, None, None, log_output_content


def execute_patch_changes(cloned_repo_dir, curr_errors, log_output_content, output_log_path, repo_name, bug_id, version, iter_count, python_ver):
    """ Execute patched build in a clean Docker environment """
    image_name = None
    if python_ver == DependencyAnalyzerConstants.PYTHON_3_8_3:
        image_name = DependencyAnalyzerConstants.PYTHON_3_8_3_IMAGE_NAME
    elif python_ver == DependencyAnalyzerConstants.PYTHON_3_8_1:
        image_name = DependencyAnalyzerConstants.PYTHON_3_8_1_IMAGE_NAME
    elif python_ver == DependencyAnalyzerConstants.PYTHON_3_7_7:
        image_name = DependencyAnalyzerConstants.PYTHON_3_7_7_IMAGE_NAME
    elif python_ver == DependencyAnalyzerConstants.PYTHON_3_7_0:
        image_name = DependencyAnalyzerConstants.PYTHON_3_7_0_IMAGE_NAME
    elif python_ver == DependencyAnalyzerConstants.PYTHON_3_6_9:
        image_name = DependencyAnalyzerConstants.PYTHON_3_6_9_IMAGE_NAME
    container_name = '{}_{}_{}'.format(repo_name, bug_id, version)
    docker_run_cmd = DependencyAnalyzerConstants.DOCKER_RUN_AS_ROOT_CMD.format(
        container_name, image_name)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        docker_run_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to run Docker container')
        return None, log_output_content
    get_container_id_cmd = DependencyAnalyzerConstants.DOCKER_GET_CONTAINER_ID_CMD + \
        container_name + DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE
    _, container_id, stderr, _ = DependencyAnalyzerUtils._run_command(
        get_container_id_cmd)
    copy_source_code_cmd = DependencyAnalyzerConstants.DOCKER_CP_HOME_CMD.format(
        cloned_repo_dir, container_id)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        copy_source_code_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to copy source code')
        return None, log_output_content
    change_perm_cmd = DependencyAnalyzerConstants.DOCKER_HOME_CHANGE_PERM_CMD.format(
        container_id, repo_name)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        change_perm_cmd)
    change_pip_perm = DependencyAnalyzerConstants.DOCKER_PIP_CHANGE_PERM_CMD.format(
        container_id)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        change_pip_perm)
    execute_build_cmd = DependencyAnalyzerConstants.DOCKER_EXEC_BUILD_JOB_CMD.format(
        container_id, repo_name)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        execute_build_cmd)
    log_cp_cmd = DependencyAnalyzerConstants.DOCKER_CP_BUILD_LOG_CMD.format(
        container_id, repo_name, output_log_path, repo_name, bug_id, version)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(log_cp_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to copy build log')
        return None, log_output_content
    remove_docker_container(container_name)
    return check_build_result(output_log_path, curr_errors, log_output_content, repo_name, bug_id, version)


def check_build_result(output_log_path, error_list, log_output_content, repo_name, bug_id, version):
    """ Check outcome of build from log file received from Docker container """
    log_contents = []
    with open(join(output_log_path, '{}_{}_{}.log'.format(repo_name, bug_id, version)),
              DependencyAnalyzerConstants.FILE_READ_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        log_contents = f.read().splitlines()
    for row_id in range(len(log_contents) - 1, 0, -1):
        if DependencyAnalyzerConstants.BUILD_SUCCESS_LOG in log_contents[row_id]:
            return BuildOutcomeType.BUILD_SUCCESSFUL, log_output_content
        else:
            match_count = 0
            for error in error_list:
                if len(error.strip()) and error in log_contents[row_id]:
                    match_count += 1
            if match_count > len(error_list)/2:
                return BuildOutcomeType.SAME_ERROR, log_output_content
    return BuildOutcomeType.NEW_ERROR, log_output_content


def create_run_dir(iter_count, dir_path):
    """ Create a directory for intermediate files of a run """
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_MKDIR.format(
        join(dir_path, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(
        join(dir_path, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))))


def get_commit_date(component_path, repo_name, bug_id, version):
    """ Get date of triggerring commit """
    bug_info_path = join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, repo_name,
                         DependencyAnalyzerConstants.BUGS_DIR, str(bug_id), DependencyAnalyzerConstants.BUG_INFO_FILENM)
    commit = None
    if version == 0:
        commit = get_value_from_info_file(
            bug_info_path, DependencyAnalyzerConstants.INFO_BUGGY_COMMIT)
    elif version == 1:
        commit = get_value_from_info_file(
            bug_info_path, DependencyAnalyzerConstants.INFO_FIXED_COMMIT)
    if not commit:
        return None
    commit = commit.replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE, DependencyAnalyzerConstants.CHAR_EMPTY)
    proj_info_path = join(
        component_path, DependencyAnalyzerConstants.PROJECTS_DIR, repo_name, DependencyAnalyzerConstants.PROJECT_INFO_FILE_NAME)
    proj_slug = get_value_from_info_file(
        proj_info_path, DependencyAnalyzerConstants.INFO_GIT_URL)
    if not proj_slug:
        return None
    proj_slug = proj_slug.replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE, DependencyAnalyzerConstants.CHAR_EMPTY)
    proj_slug = proj_slug.replace(
        DependencyAnalyzerConstants.GITHUB_URL, DependencyAnalyzerConstants.CHAR_EMPTY)
    git_commit_api_url = DependencyAnalyzerConstants.GITHUB_COMMITS_API_URL.format(
        proj_slug, commit)
    git_commit_details = requests.get(git_commit_api_url, auth=(
        DependencyAnalyzerConstants.GITHUB_USER_NAME, DependencyAnalyzerConstants.GITHUB_AUTH_TOKEN))
    if git_commit_details.status_code != HTTPStatus.OK:
        return None
    git_commit_details = git_commit_details.json()
    if DependencyAnalyzerConstants.GITHUB_JSON_COMMIT_KEY in git_commit_details and 'author' in git_commit_details[DependencyAnalyzerConstants.GITHUB_JSON_COMMIT_KEY] and 'date' in git_commit_details[DependencyAnalyzerConstants.GITHUB_JSON_COMMIT_KEY]['author']:
        return git_commit_details[DependencyAnalyzerConstants.GITHUB_JSON_COMMIT_KEY]['author']['date']
    return None


def get_value_from_info_file(info_file_path, start_key):
    """ get value from bugs.info or project.info, files which are part of the
        metadata of BugsInPy dataset """
    if not isfile(info_file_path):
        return None
    with open(info_file_path, DependencyAnalyzerConstants.FILE_READ_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        info_file_contents = [x.strip() for x in f.readlines()]
    for line in info_file_contents:
        if line.startswith(start_key):
            return line.split(start_key)[-1].strip(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE)
    return None


def copy_build_script(component_path, cloned_dir, repo_name, bug_id, version):
    """ Create build script in cloned directory """
    travis_gen = TravisYMLGenerator()
    travis_gen.bugsinpy_yaml_generation('{}_{}_{}'.format(repo_name, bug_id, version), component_path, os.getcwd(), True)
    inner_dir = repo_name
    if inner_dir == 'spacy':
        inner_dir = 'spaCy'
    cp_travis_yml_cmd = 'cp {}_{}_{}/.travis.yml {}_{}_{}/{}'.format(
        repo_name, bug_id, version, repo_name, bug_id, version, inner_dir)
    cp_travis_script_cmd = 'cp {}_{}_{}/test.sh {}_{}_{}/{}'.format(
        repo_name, bug_id, version, repo_name, bug_id, version, inner_dir)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        ';'.join([cp_travis_yml_cmd, cp_travis_script_cmd]))
    if not ok:
        return False
    script_content = []
    with open(join(cloned_dir, 'test.sh'), DependencyAnalyzerConstants.FILE_READ_MODE) as f:
        script_content = f.readlines()
    edited_script = []
    for line in script_content:
        if not line.strip().startswith('travis_cmd cd\ /home/sumukher/bugswarm-dev/dependency-solver/scripts/'):
            edited_script.append(line)
        else:
            edited_script.append(
                '  travis_cmd cd\{} --assert --echo'.format(cloned_dir))
    with open(join(cloned_dir, 'test.sh'), DependencyAnalyzerConstants.FILE_WRITE_MODE) as f:
        f.write(DependencyAnalyzerConstants.CHAR_EMPTY.join(edited_script))
    return True


def setup_bug_repo(component_path, repo_name, bug_id, version):
    """ Setup cloned source code """
    project_info_locn = join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR,
                             repo_name, DependencyAnalyzerConstants.PROJECT_INFO_FILE_NAME)
    bug_info_locn = join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, repo_name,
                         DependencyAnalyzerConstants.BUGS_DIR, bug_id, DependencyAnalyzerConstants.BUG_INFO_FILENM)
    git_repo_url = get_value_from_info_file(
        project_info_locn, DependencyAnalyzerConstants.INFO_GIT_URL)
    outer_dir_name = '{}_{}_{}'.format(repo_name, bug_id, version)
    if repo_name == 'spacy':
        clone_dir = join(os.getcwd(), outer_dir_name, 'spaCy')
    else:
        clone_dir = join(os.getcwd(), outer_dir_name, repo_name)
    if not git_repo_url:
        return None
    if isdir(clone_dir) or isdir(join(os.getcwd(), outer_dir_name)):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.SUDO_RM_RF_CMD.format(join(os.getcwd(), outer_dir_name)))
    git_clone_cmd = DependencyAnalyzerConstants.GIT_CLONE_CMD.format(
        outer_dir_name, outer_dir_name, git_repo_url.strip(DependencyAnalyzerConstants.CHAR_SLASH))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(git_clone_cmd)
    if not ok:
        print(stderr)
        print('Failed to clone repo')
        return None
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(clone_dir))
    if not ok:
        print(stderr)
        print('Failed to change permission for cloned repo')
        return None
    failed_commit = get_value_from_info_file(
        bug_info_locn, DependencyAnalyzerConstants.INFO_BUGGY_COMMIT)
    passed_commit = get_value_from_info_file(
        bug_info_locn, DependencyAnalyzerConstants.INFO_FIXED_COMMIT)
    test_file_locn = get_value_from_info_file(
        bug_info_locn, DependencyAnalyzerConstants.INFO_TEST_FILE)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        DependencyAnalyzerConstants.GIT_RESET_HARD_CMD.format(clone_dir, passed_commit))
    if not ok:
        print(stderr)
        print('Failed to reset head of cloned repo to passed commit')
        return None
    if version == 0:  # failed version
        test_file_contents = get_test_file_contents(clone_dir, test_file_locn)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.GIT_RESET_HARD_CMD.format(clone_dir, failed_commit))
        if not ok:
            print(stderr)
            print('Failed to reset head of cloned repo to failed commit')
            return None
        if test_file_contents:
            write_test_file_contents(
                clone_dir, test_file_locn, test_file_contents)
    return clone_dir


def write_test_file_contents(clone_dir, test_file_locn, test_file_contents):
    """ Add failing tests to source code """
    with open(join(clone_dir, test_file_locn), DependencyAnalyzerConstants.FILE_WRITE_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        f.write(DependencyAnalyzerConstants.CHAR_NEW_LINE.join(test_file_contents))


def get_test_file_contents(clone_dir, test_file_locn):
    """ Read failing tests from test file """
    test_file_contents = None
    if not isfile(join(clone_dir, test_file_locn)):
        return None
    with open(join(clone_dir, test_file_locn), DependencyAnalyzerConstants.FILE_READ_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        test_file_contents = [x for x in f.readlines()]
    return test_file_contents


def get_bug_details(log_file_name):
    """ Get build details from build log file name """
    name_split_list = log_file_name.replace(DependencyAnalyzerConstants.LOG_FILE_EXT, DependencyAnalyzerConstants.CHAR_EMPTY).split(
        DependencyAnalyzerConstants.CHAR_UNDERSCORE)
    try:
        version = int(name_split_list[2].strip())
        return name_split_list[0].strip(), name_split_list[1].strip(), version
    except Exception as e:
        traceback.print_exc()
        print('Unable to extract bug details from log file name')
        return None, None, None


def get_log_analyzer_results(file_path):
    """ Read results from csv output of LogErrorAnalyzer """
    content = []
    with open(join(file_path, 'bugsinpy_artifacts_dependency_broken.csv'),
              DependencyAnalyzerConstants.FILE_READ_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            content.append(row)
    return content


def cleanup(component_path, output_log_path=None, log_output_content=None, repo_dir=None):
    """ Remove intermediate details """
    if output_log_path:
        append_output_log(output_log_path, log_output_content)
        log_output_content = []
    if repo_dir:
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.SUDO_RM_RF_CMD.format(repo_dir))


def remove_docker_container(container_name):
    """ Remove Docker container used """
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
        DependencyAnalyzerConstants.DOCKER_REMOVE_CONTAINER.format(container_name))


def append_output_log(log_path, content):
    """ Write to output log """
    with open(join(log_path, DependencyAnalyzerConstants.OUTPUT_LOG), DependencyAnalyzerConstants.FILE_ACCESS_MODE) as f:
        for i in content:
            f.write(i + DependencyAnalyzerConstants.CHAR_NEW_LINE)
        f.write(DependencyAnalyzerConstants.CHAR_NEW_LINE)


if __name__ == '__main__':
    # python3 bugsinpy_automate_iterative_dependency_solver.py
    # -path <path to bugsinpy_artifacts_dependency_broken.csv>
    # -originallogs <path to original logs>
    # -component <path to bugsinpy component>
    # -intermediates <path to intermediate folder>
    main(sys.argv)
