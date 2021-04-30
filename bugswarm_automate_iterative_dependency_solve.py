import os
from os.path import join, isdir, expanduser, isfile
import pathlib
import sys
import json
import csv
import yaml
import traceback
import time
import requests
from multiprocessing import Pool, cpu_count
from functools import partial
import zipfile
import shutil
from pathlib import Path
from http import HTTPStatus
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from build_outcome_type import BuildOutcomeType
from bugswarm.analyzer.analyzer import Analyzer
from solver_utils import SolverUtils
from final_outcome import FinalOutcome


""" Implementation of IterativeDependencySolver for BugSwarm """


def main(args):
    overall_start_time = time.time()
    input_files_path = args[2]
    orig_log_path = args[4]
    source_code_path = args[6]
    intermediate_path = args[8]
    artifact_dict = DependencyAnalyzerUtils.get_artifact_dict(input_files_path)
    fix_file_contents = get_dependency_analyzer_results(input_files_path)
    with Pool(cpu_count()) as pool:
        results = pool.map(partial(process_each_artifact_dependency_solve,
                           artifact_dict=artifact_dict,
                           intermediate_path=intermediate_path,
                           source_code_path=source_code_path,
                           orig_log_path=orig_log_path), fix_file_contents)
    results = [line[0] for line in results]
    DependencyAnalyzerUtils.write_to_csv(results, DependencyAnalyzerConstants.BUGSWARM_CSV_SOLVER_RESULTS_HEADERS, 'iterative_solve_results.csv')
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
        print('Partial Fixes: {}({})'.format(partial_fix, partial_fix*100/len(results)))
        print('No Fixes: {}({})'.format(len(results) - (complete_fix + partial_fix), (len(results) - (complete_fix + partial_fix))*100/len(results)))
        print('Total Runtime: {} minutes'.format((overall_end_time - overall_start_time)/60))
    print('==========**** END OF OUTPUT ****==========')


def create_artifact_dir(artifact, f_or_p, intermediate_path):
    """ Create directories for storing intermediate results of while
        solving a build """
    dir_path = '{}/{}/{}'.format(intermediate_path, artifact, f_or_p)
    if isdir(dir_path):
        return
    if not isdir(join(intermediate_path, artifact)):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_MKDIR.format(join(intermediate_path, artifact)))
    if not isdir(join(intermediate_path, artifact, f_or_p)):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_MKDIR.format(join(intermediate_path, artifact, f_or_p)))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(intermediate_path, artifact, f_or_p)))


def create_run_dir(iter_count, dir_path):
    """ Create a directory for storing intermediate results of a run while
        solving a build """
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_MKDIR.format(join(dir_path, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(dir_path, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))))


def append_output_log(log_path, content):
    with open(join(log_path, DependencyAnalyzerConstants.OUTPUT_LOG), DependencyAnalyzerConstants.FILE_ACCESS_MODE) as f:
        for i in content:
            f.write(i + DependencyAnalyzerConstants.CHAR_NEW_LINE)
        f.write(DependencyAnalyzerConstants.CHAR_NEW_LINE)


def process_each_artifact_dependency_solve(fix_file_row, artifact_dict, intermediate_path, source_code_path, orig_log_path):
    """ Process each artifact by generating and applying patches """
    final_output = []
    start_time = time.time()
    accepted_patch_str = DependencyAnalyzerConstants.CHAR_EMPTY
    log_output_content = []
    log_file_name = fix_file_row[0].strip()
    analyzer_result = None
    artifact, f_or_p = extract_from_file_name(log_file_name, artifact_dict)
    final_iter_count = 0
    try:
        solve_result = None
        analyzer_result = None
        cleanup()
        output_path = join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p)
        create_artifact_dir(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p, intermediate_path)
        commit_date = artifact[DependencyAnalyzerConstants.JOB_KEY.format(f_or_p)][DependencyAnalyzerConstants.COMMITTED_AT_KEY]
        print('Processing....{}_{}'.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p))
        # Step1: Get source code from GitHub
        cloned_repo_dir, log_output_content = clone_repo(artifact, f_or_p, log_output_content, source_code_path)
        if not cloned_repo_dir:
            solve_result = FinalOutcome.FAILED_SOURCE_CODE_CLONE
            cleanup(None, output_path, log_output_content)
            final_output.append([log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, analyzer_result, (time.time() - start_time), final_iter_count])
            return final_output
        possible_candidates = json.loads(fix_file_row[2])
        # Step 2: Modify .travis.yml
        modified_travis_yml, log_output_content = modify_travis_yml(f_or_p, cloned_repo_dir, artifact[DependencyAnalyzerConstants.REPO_KEY], log_output_content)
        if not modified_travis_yml:
            cleanup(None, output_path, log_output_content, cloned_repo_dir)
            solve_result = FinalOutcome.FAILED_UNABLE_TO_MODIFY_TRAVIS_YML
            final_output.append([log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, analyzer_result, (time.time() - start_time), final_iter_count])
            return final_output
        # Step3: Generate test.sh script with travis-build
        generated_build_sh, log_output_content = generate_and_prepare_build_script(f_or_p, cloned_repo_dir, artifact[DependencyAnalyzerConstants.REPO_KEY], log_output_content)
        if not generated_build_sh:
            log_output_content.append(FinalOutcome.FAILED_TO_PREPARE_BUILD_SCRIPT)
            solve_result = FinalOutcome.FAILED_TO_PREPARE_BUILD_SCRIPT
            cleanup(None, output_path, log_output_content, cloned_repo_dir)
            final_output.append([log_file_name, DependencyAnalyzerConstants.CHAR_EMPTY, solve_result, analyzer_result, (time.time() - start_time), final_iter_count])
            return final_output
        # Step4: Pinning correct versions for possible candidates
        dep_files = fix_file_row[3].strip()
        patches, log_output_content = SolverUtils.generate_patch_combos(possible_candidates, commit_date, artifact[DependencyAnalyzerConstants.REPO_KEY], log_output_content, cloned_repo_dir, dep_files)
        # Step5: Copy files to container to make changes except patch_requirements.txt
        curr_errors = fix_file_row[1].split(DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
        run_solver = True
        curr_patch_str = DependencyAnalyzerConstants.CHAR_EMPTY
        accepted_patch_str = DependencyAnalyzerConstants.CHAR_EMPTY
        iter_count = -1
        # Step6: Run iterative solver
        while(run_solver):
            iter_count += 1
            final_iter_count += 1
            output_log_path = join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))
            create_run_dir(iter_count, join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p,))
            found_new_patch = False
            curr_patch_str = accepted_patch_str

            # write available patch combinations to intermediate directory for record keeping
            with open(join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count), DependencyAnalyzerConstants.PATCH_COMBO_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_PLUS_MODE) as f:
                f.write(json.dumps(patches))
            accepted_patch_list = accepted_patch_str.split(DependencyAnalyzerConstants.CHAR_NEW_LINE)
            
            # Step6a: Get patch
            for patch in patches:
                most_probable_patch = patches[0]
                if [p for p in accepted_patch_list if p.strip(DependencyAnalyzerConstants.CHAR_NEW_LINE).startswith(patch[DependencyAnalyzerConstants.NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS)]:
                    if not most_probable_patch[DependencyAnalyzerConstants.APPLIED_KEY] and patch[DependencyAnalyzerConstants.NAME_KEY] == most_probable_patch[DependencyAnalyzerConstants.NAME_KEY] and accepted_patch_list[-1].strip(DependencyAnalyzerConstants.CHAR_NEW_LINE).startswith(patch[DependencyAnalyzerConstants.NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS) and accepted_patch_list[-1].strip(DependencyAnalyzerConstants.CHAR_NEW_LINE).split(DependencyAnalyzerConstants.STR_EQUALS)[-1] != patch[DependencyAnalyzerConstants.VERSION_KEY]:
                        del accepted_patch_list[-1]
                        accepted_patch_str = DependencyAnalyzerConstants.CHAR_NEW_LINE.join(accepted_patch_list)
                    else:
                        continue
                if patch[DependencyAnalyzerConstants.INCLUDED_KEY] or patch[DependencyAnalyzerConstants.APPLIED_KEY]:
                    continue
                if len(patch[DependencyAnalyzerConstants.NAME_KEY]) == 0:
                    curr_patch_str = accepted_patch_str + patch[DependencyAnalyzerConstants.NAME_KEY] + DependencyAnalyzerConstants.CHAR_NEW_LINE
                else:
                    curr_patch_str = accepted_patch_str + patch[DependencyAnalyzerConstants.NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS + patch[DependencyAnalyzerConstants.VERSION_KEY] + DependencyAnalyzerConstants.CHAR_NEW_LINE
                patch[DependencyAnalyzerConstants.APPLIED_KEY] = True
                found_new_patch = True
                break

            # If no unapplied patches are found
            if not found_new_patch:
                use_iter_count = iter_count
                if iter_count > 0:
                    use_iter_count = iter_count - 1

                # Check if problem has been solved
                if check_if_restored_to_original_error(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], artifact[DependencyAnalyzerConstants.JOB_KEY.format(f_or_p)][DependencyAnalyzerConstants.JOB_ID_KEY], use_iter_count, f_or_p, orig_log_path):
                    # The current log matches the original log
                    log_output_content.append(FinalOutcome.SUCCESS_RESTORED_TO_ORIGINAL_STATUS)
                    solve_result = FinalOutcome.SUCCESS_RESTORED_TO_ORIGINAL_STATUS
                    analyzer_result = True
                else:
                    # The current log does not match the original log
                    analyzer_result = False
                    log_output_content.append(FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS)
                    solve_result = FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS
                cleanup(DependencyAnalyzerConstants.ARTIFACT_DIR.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p), output_log_path, log_output_content, cloned_repo_dir)
                break

            # write current patch to intermediate directory for record keeping
            with open(join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count), DependencyAnalyzerConstants.PATCH_DEPENDENCY_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_PLUS_MODE) as f:
                f.write(curr_patch_str)

            # write current patch to cloned directory for new build
            with open(join(cloned_repo_dir, DependencyAnalyzerConstants.PATCH_DEPENDENCY_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_MODE) as f:
                f.write(curr_patch_str)

            # Step6b: Apply patch, check outcome
            SolverUtils.remove_docker_container(DependencyAnalyzerConstants.ARTIFACT_DIR.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p))
            container_id, log_output_content = copy_files_to_container(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], cloned_repo_dir, f_or_p, log_output_content, artifact[DependencyAnalyzerConstants.REPO_KEY])

            # If failed to run Docker container
            if not container_id:
                log_output_content.append(FinalOutcome.FAILED_TO_RUN_DOCKER)
                cleanup(DependencyAnalyzerConstants.ARTIFACT_DIR.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p), output_log_path, log_output_content, cloned_repo_dir)
                solve_result = FinalOutcome.FAILED_TO_RUN_DOCKER
                break

            build_outcome, log_output_content = execute_patch_changes(container_id, f_or_p, artifact, curr_errors, log_output_content)

            # If failed to run build
            if not build_outcome:
                cleanup(DependencyAnalyzerConstants.ARTIFACT_DIR.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p), output_log_path, log_output_content, cloned_repo_dir)
                solve_result = FinalOutcome.FAILED_NO_BUILD_OUTCOME
                log_output_content.append(FinalOutcome.FAILED_NO_BUILD_OUTCOME)
                break

            # Copying build logs for LogErrorAnalyzer
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
                DependencyAnalyzerConstants.COPY_BUGSWARM_SANDBOX_LOG.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p, join(intermediate_path,
                                                                                               artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY],
                                                                                               f_or_p,
                                                                                               DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))))

            # If build is successful
            if build_outcome == BuildOutcomeType.BUILD_SUCCESSFUL:
                log_output_content.append(FinalOutcome.SUCCESS_FIXED_BUILD)
                accepted_patch_str = curr_patch_str
                cleanup(DependencyAnalyzerConstants.ARTIFACT_DIR.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p), output_log_path, log_output_content, cloned_repo_dir)
                solve_result = FinalOutcome.SUCCESS_FIXED_BUILD
                use_iter_count = iter_count
                if iter_count > 0:
                    use_iter_count = iter_count - 1
                if check_if_restored_to_original_error(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], artifact[DependencyAnalyzerConstants.JOB_KEY.format(f_or_p)][DependencyAnalyzerConstants.JOB_ID_KEY], use_iter_count, f_or_p, orig_log_path):
                    analyzer_result = True
                else:
                    analyzer_result = False
                break
            else:
                new_errors, candidates_found, new_dep_files, log_output_content = run_log_analyzer(artifact, f_or_p, fix_file_row[0], intermediate_path, iter_count, log_output_content)
                if not candidates_found:
                    if check_if_restored_to_original_error(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], artifact[DependencyAnalyzerConstants.JOB_KEY.format(f_or_p)][DependencyAnalyzerConstants.JOB_ID_KEY], iter_count, f_or_p, orig_log_path):
                        log_output_content.append(FinalOutcome.SUCCESS_RESTORED_TO_ORIGINAL_ERROR)
                        solve_result = FinalOutcome.SUCCESS_RESTORED_TO_ORIGINAL_ERROR
                        analyzer_result = True
                    else:
                        analyzer_result = False
                        if not new_errors:
                            log_output_content.append(FinalOutcome.SUCCESS_NO_LONGER_DEPENDENCY_ERROR)
                            solve_result = FinalOutcome.SUCCESS_NO_LONGER_DEPENDENCY_ERROR
                        else:
                            log_output_content.append(FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS)
                            solve_result = FinalOutcome.PARTIAL_EXHAUSTED_ALL_OPTIONS
                    accepted_patch_str = curr_patch_str
                    cleanup(DependencyAnalyzerConstants.ARTIFACT_DIR.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p), output_log_path, log_output_content, cloned_repo_dir)
                    break

                new_candidates_found = False
                last_added_patch_caused_error = False
                most_probable_candidate = candidates_found[0]
                last_added_patch = curr_patch_str.strip(DependencyAnalyzerConstants.CHAR_NEW_LINE).split(DependencyAnalyzerConstants.CHAR_NEW_LINE)[-1]

                if len(new_errors):
                    # Check if last added patch caused error
                    if not last_added_patch_caused_error and last_added_patch.startswith(most_probable_candidate[DependencyAnalyzerConstants.CANDIDATE_NAME_KEY] + DependencyAnalyzerConstants.STR_EQUALS):
                        last_added_patch_caused_error = True

                    # check if any new candidates have been found
                    for candidate in candidates_found:
                        is_new_candidate = True
                        for prev_candidate in possible_candidates:
                            if prev_candidate[DependencyAnalyzerConstants.CANDIDATE_NAME_KEY] == candidate[DependencyAnalyzerConstants.CANDIDATE_NAME_KEY] and prev_candidate[DependencyAnalyzerConstants.CANDIDATE_VERSION_CONSTRAINT_KEY] == candidate[DependencyAnalyzerConstants.CANDIDATE_VERSION_CONSTRAINT_KEY]:
                                is_new_candidate = False
                                break
                        if is_new_candidate:
                            new_candidates_found = True
                            break

                if build_outcome == BuildOutcomeType.NEW_ERROR and last_added_patch_caused_error:
                    # include new candidates if found else discard current candidate
                    if new_candidates_found:
                        curr_errors = new_errors.split(DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
                        patches, log_output_content = SolverUtils.generate_patch_combos(candidates_found[1:], commit_date, artifact[DependencyAnalyzerConstants.REPO_KEY], log_output_content, cloned_repo_dir, new_dep_files)
                    log_output_content.append('Last added patch caused new error...discarding')
                elif build_outcome == BuildOutcomeType.NEW_ERROR or \
                        (build_outcome == BuildOutcomeType.SAME_ERROR and new_candidates_found):
                    # Discard all current candidates
                    log_output_content.append('Build error changed or new candidates found')
                    accepted_patch_str = curr_patch_str
                    curr_errors = new_errors.split(DependencyAnalyzerConstants.ERROR_LINE_DELIMITER)
                    patches, log_output_content = SolverUtils.generate_patch_combos(candidates_found, commit_date, artifact[DependencyAnalyzerConstants.REPO_KEY], log_output_content, cloned_repo_dir, new_dep_files)
                    possible_candidates = candidates_found
                else:
                    log_output_content.append('Reject current incremental patch as it did not change error')
    except Exception as e:
        traceback.print_exc()
        print(log_output_content)
        log_output_content = []
        solve_result = FinalOutcome.FAILED_ERROR.format(e)
    end_time = time.time()
    final_output.append([log_file_name, accepted_patch_str.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE, DependencyAnalyzerConstants.CHAR_SPACE), solve_result, analyzer_result, (end_time - start_time), final_iter_count])
    log_output_content.append(accepted_patch_str)
    append_output_log(join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p), log_output_content)
    return final_output


def check_if_restored_to_original_error(intermediate_path, img_tag, job_id, iter_count, f_or_p, orig_log_path):
    """ Compare current build to original build """
    log_path = join(intermediate_path, img_tag, f_or_p, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))
    repro_log_path = join(log_path, DependencyAnalyzerConstants.LOG_FILE_NM_PATTERN.format(img_tag, f_or_p))
    orig_log_name = '{}.{}.orig.log'.format(img_tag, f_or_p)
    if not isfile(join(orig_log_path, orig_log_name)):
        return False
    if not isfile(repro_log_path):
        return False
    analyzer = Analyzer()
    try:
        success, attr_list = analyzer.compare_single_log(repro_log_path, join(orig_log_path,orig_log_name), job_id)
        if not success:
            for attr in attr_list:
                if attr[DependencyAnalyzerConstants.ATTR_KEY] in [DependencyAnalyzerConstants.LOG_STATUS_KEY,
                                                                DependencyAnalyzerConstants.LOG_TESTS_RUN_KEY,
                                                                DependencyAnalyzerConstants.LOG_TESTS_FAILED_KEY]:
                    return False
    except Exception as e:
        print(e)
        return False
    return True


def clone_repo(artifact, f_or_p, log_output_content, source_code_path):
    """ Get Source code """
    # return join(source_code_path,
    # artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY] +
    # DependencyAnalyzerConstants.CHAR_UNDERSCORE + f_or_p), log_output_content
    clone_location = join(source_code_path, '{}_{}'.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p))
    if isdir(clone_location):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_RM_RF_CMD.format(clone_location))
    diff_url = artifact[DependencyAnalyzerConstants.DIFF_URL_KEY]
    response = requests.get(diff_url, auth=(
        DependencyAnalyzerConstants.GITHUB_USER_NAME, DependencyAnalyzerConstants.GITHUB_AUTH_TOKEN))
    if response.status_code != HTTPStatus.OK:
        log_output_content.append('Diff not found')
        return None, log_output_content
    if f_or_p == DependencyAnalyzerConstants.STR_FAILED:
        commit = diff_url.split(DependencyAnalyzerConstants.STR_TWO_DOTS)[0].split(DependencyAnalyzerConstants.CHAR_SLASH)[-1]
    else:
        commit = diff_url.split(DependencyAnalyzerConstants.STR_TWO_DOTS)[-1]
    zip_download_url = DependencyAnalyzerConstants.GITHUB_ARCHIVE_API_URL.format(artifact[DependencyAnalyzerConstants.REPO_KEY], commit)
    response = requests.get(zip_download_url, stream=True, auth=(
        DependencyAnalyzerConstants.GITHUB_USER_NAME, DependencyAnalyzerConstants.GITHUB_AUTH_TOKEN))
    if response.status_code != HTTPStatus.OK:
        log_output_content.append('Failed to get source code for failed commit from git archive')
        return None, log_output_content
    resp_zip = '{}_{}.zip'.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p)
    log_output_content.append('Successful to get source code for failed commit')
    handle = open(resp_zip, "wb")
    for chunk in response.iter_content(chunk_size=512):
        if chunk:  # filter out keep-alive new chunks
            handle.write(chunk)
    handle.close()
    with zipfile.ZipFile(resp_zip, DependencyAnalyzerConstants.FILE_READ_MODE) as f:
        inner_dir = list({item.split(DependencyAnalyzerConstants.CHAR_SLASH)[0] for item in f.namelist()})[0]
    with zipfile.ZipFile(join(os.getcwd(), resp_zip), DependencyAnalyzerConstants.FILE_READ_MODE) as zip_ref:
        zip_ref.extractall(clone_location)
    for each_file in Path(join(clone_location, inner_dir)).glob('*.*'):
        trg_path = each_file.parent.parent
        each_file.rename(trg_path.joinpath(each_file.name))
    shutil.rmtree(join(clone_location, inner_dir))
    if os.path.exists(join(os.getcwd(), resp_zip)):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_RM_CMD.format(join(os.getcwd(), resp_zip)))
    return clone_location, log_output_content


def execute_patch_changes(container_id, f_or_p, artifact, curr_errors, log_output_content):
    """ Copy patch_requirements.txt to Docker container and re-run build job """
    execute_script_in_container(container_id, f_or_p, artifact[DependencyAnalyzerConstants.REPO_KEY], DependencyAnalyzerConstants.GENERATED_BUILD_SCRIPT_NAME, log_output_content, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY])
    return check_build_result(f_or_p, curr_errors, log_output_content, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY])


def run_log_analyzer(artifact, f_or_p, log_file_nm, intermediate_path, iter_count, log_output_content):
    """ Run log analyzer to check if a dependency issue still exists, if it does what are the errors and what are the possible candidates """
    if not isdir(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE), DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR)):
        mkdir_log_path_cmd = DependencyAnalyzerConstants.CREATE_DIR_CMD.format(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                               DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(mkdir_log_path_cmd)
        if not ok:
            log_output_content.append(stderr)
            log_output_content.append('Failed to create intermediate log folder')
            print('Failed to create intermediate log folder')
            return None, None, None, log_output_content
    change_per_cmd = DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                              DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(change_per_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to change permission')
        print('Failed to change permission')
        return None, None, None, log_output_content
    cp_log_cmd = DependencyAnalyzerConstants.COPY_FILE_CMD.format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                       DependencyAnalyzerConstants.BUGSWARM_CLIENT_SANDBOX,
                                                                       DependencyAnalyzerConstants.LOG_FILE_NM_PATTERN.format(artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY], f_or_p)),
                                                                  join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                       DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR,
                                                                       log_file_nm))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_log_cmd)
    if not ok:
        print(stderr)
        log_output_content.append(stderr)
        log_output_content.append('Failed to copy new log')
        print('Failed to copy new log')
        return None, None, None, log_output_content
    cp_art_cmd = DependencyAnalyzerConstants.COPY_FILE_CMD.format(DependencyAnalyzerConstants.ARTIFACTS_JSON_FILE_NAME,
                                                                 join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                      DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_art_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to copy artifacts.json')
        print('Failed to copy artifacts.json')
        return None, None, None, log_output_content
    log_analyzer_cmd = DependencyAnalyzerConstants.BUGSWARM_RUN_LOG_ANALYZER\
        .format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE), DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR), log_file_nm)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(log_analyzer_cmd)
    log_output_content.append(stdout)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to run log analyzer')
        print('Failed to run log analyzer')
        return None, None, None, log_output_content
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('cp {} {}'.format('artifacts_dependency_broken_' + log_file_nm.split()[0] + '.csv',
                                                                                    join(intermediate_path, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY],
                                                                                          f_or_p, DependencyAnalyzerConstants.ITER_RUN_DIR_NAME.format(iter_count))))
    errors = None
    candidates = None
    files = None
    found_row = False
    with open('artifacts_dependency_broken_' + log_file_nm.split()[0] + '.csv', DependencyAnalyzerConstants.FILE_READ_MODE) as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            found_row = True
            errors = row[1]
            candidates = json.loads(row[2])
            files = row[3]
            break
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.SUDO_RM_CMD.format('artifacts_dependency_broken_' + log_file_nm.split()[0] + '.csv'))
    if found_row:
        return errors, candidates, files, log_output_content
    return None, None, None, log_output_content


def check_build_result(f_or_p, error_list, log_output_content, img_tag):
    """ Check outcome of build from log file received from Docker container """
    log_contents = []
    with open(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                   DependencyAnalyzerConstants.BUGSWARM_CLIENT_SANDBOX,
                   DependencyAnalyzerConstants.LOG_FILE_NM_PATTERN.format(img_tag, f_or_p)),
              DependencyAnalyzerConstants.FILE_READ_MODE) as f:
        log_contents = f.read().splitlines()
    for row_id in range(len(log_contents) - 1, 0, -1):
        if DependencyAnalyzerConstants.BUILD_SUCCESS_LOG in log_contents[row_id]:
            return BuildOutcomeType.BUILD_SUCCESSFUL, log_output_content
        else:
            for error in error_list:
                if len(error.strip()) and error in log_contents[row_id]:
                    return BuildOutcomeType.SAME_ERROR, log_output_content
    return BuildOutcomeType.NEW_ERROR, log_output_content


def execute_script_in_container(container_id, f_or_p, repo_dir_name, build_script_name, log_output_content, img_tag):
    """ Execute script in container which will start travis job in Docker and copy the log
        back to host """
    docker_exec_cmd = DependencyAnalyzerConstants.DOCKER_EXEC_SCRIPT_CMD.format(container_id, f_or_p, repo_dir_name,
                                                                                        build_script_name)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_exec_cmd)
    if not ok:
        log_output_content.append('Failed to execute script insideDocker container')
        return False, log_output_content
    log_output_content.append('Successfully executed script in container')

    # copying log from container
    docker_log_cp_cmd = DependencyAnalyzerConstants.DOCKER_LOG_CP_CMD.format(container_id,
                                                                             f_or_p,
                                                                             join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                                  DependencyAnalyzerConstants.BUGSWARM_CLIENT_SANDBOX,
                                                                                  DependencyAnalyzerConstants.LOG_FILE_NM_PATTERN.format(img_tag, f_or_p)))
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_log_cp_cmd)
    if not ok:
        log_output_content.append('Failed to copy log from Docker container')
        return False, log_output_content
    log_output_content.append('Successfully copied log from container')
    return True, log_output_content


def copy_files_to_container(img_tag, cloned_repo_dir, f_or_p, log_output_content, repo_name):
    """ Copy build script, source code and python script to run travis build to container """
    container_name = DependencyAnalyzerConstants.ARTIFACT_DIR.format(img_tag, f_or_p)
    docker_container_cmd = DependencyAnalyzerConstants.DOCKER_RUN_IMAGE_CMD.format(container_name, img_tag)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_container_cmd)
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Failed to run Docker container')
        return None, log_output_content
    get_container_id_cmd = DependencyAnalyzerConstants.DOCKER_GET_CONTAINER_ID_CMD + container_name + '"'
    _, container_id, stderr, _ = DependencyAnalyzerUtils._run_command(get_container_id_cmd)
    copy_file_cmd = DependencyAnalyzerConstants.DOCKER_COPY_SCRIPT_CMD.format(container_id)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(copy_file_cmd)
    if not ok:
        log_output_content.append('Failed to copy file to Docker container')
        return None, log_output_content
    log_output_content.append('Successfully copied script to container')
    build_script_path = join(cloned_repo_dir, DependencyAnalyzerConstants.GENERATED_BUILD_SCRIPT_NAME)
    repo_dir_path = pathlib.Path(cloned_repo_dir).parent
    cp_build_script_cmd = DependencyAnalyzerConstants.DOCKER_COPY_BUILD_SCRIPT_CMD\
        .format(build_script_path, container_id, f_or_p)
    cp_repo_dir_cmd = DependencyAnalyzerConstants.DOCKER_COPY_SOURCE_CODE_CMD.format(cloned_repo_dir, container_id, f_or_p, repo_name)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_build_script_cmd)
    if not ok:
        DependencyAnalyzerUtils.print_error_msg(stderr, 'Unable to copy build script', cp_build_script_cmd)
        return None, log_output_content
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_repo_dir_cmd)
    if not ok:
        DependencyAnalyzerUtils.print_error_msg(stderr, 'Unable to copy source code', cp_repo_dir_cmd)
        return None, log_output_content
    return container_id, log_output_content


def modify_travis_yml(f_or_p, cloned_repo_dir, repo, log_output_content):
    """ Modify .travis.yml to install patch dependencies before project dependencies """
    with open(join(cloned_repo_dir, DependencyAnalyzerConstants.TRAVIS_YAML_FILE_NAME), DependencyAnalyzerConstants.FILE_READ_MODE) as f:
        yaml_content_dict = yaml.load(f, Loader=yaml.FullLoader)
    yaml_content_dict = remove_upgrade_option(yaml_content_dict)
    pip_install_found, modified_dict = modify_install_step(yaml_content_dict, DependencyAnalyzerConstants.TRAVIS_BEFORE_INSTALL, f_or_p, repo)
    if not pip_install_found:
        pip_install_found, modified_dict = modify_install_step(yaml_content_dict, DependencyAnalyzerConstants.TRAVIS_INSTALL, f_or_p, repo)
    if not pip_install_found:
        log_output_content.append('Unable to find pip install step...trying to find the install stage')
        install_found, modified_dict = modify_install_step(yaml_content_dict, DependencyAnalyzerConstants.TRAVIS_INSTALL, f_or_p, repo, False)
        if not install_found:
            added_install, modified_dict = add_install_step(yaml_content_dict, f_or_p, repo)
            if not added_install:
                log_output_content.append('Unable to add install step...trying to find the install stage')
                return False, log_output_content
    with open(join(cloned_repo_dir, DependencyAnalyzerConstants.TRAVIS_YAML_FILE_NAME), DependencyAnalyzerConstants.FILE_WRITE_MODE) as f:
        yaml.dump(modified_dict, f)
    log_output_content.append('Successfully added install step for patch_requirements')
    return True, log_output_content


def add_install_step(yaml_content_dict, f_or_p, repo):
    modified_dict = {}
    inserted_install_step = False
    for key in yaml_content_dict:
        if not inserted_install_step and key == DependencyAnalyzerConstants.TRAVIS_BEFORE_INSTALL:
            modified_dict[key] = yaml_content_dict[key]
            modified_dict[DependencyAnalyzerConstants.TRAVIS_INSTALL] = [DependencyAnalyzerConstants.PIP_INSTALL_PATCH.format(f_or_p, repo)]
        elif not inserted_install_step and key == DependencyAnalyzerConstants.TRAVIS_SCRIPT:
            modified_dict[DependencyAnalyzerConstants.TRAVIS_INSTALL] = [DependencyAnalyzerConstants.PIP_INSTALL_PATCH.format(f_or_p, repo)]
            modified_dict[key] = yaml_content_dict[key]
        else:
            modified_dict[key] = yaml_content_dict[key]
    return inserted_install_step, modified_dict


def remove_upgrade_option(content):
    if isinstance(content, str):
        content = content.replace(DependencyAnalyzerConstants.PIP_INSTALL_UPGRADE_FLAG, DependencyAnalyzerConstants.PIP_INSTALL).replace(DependencyAnalyzerConstants.PIP_INSTALL_U_FLAG, DependencyAnalyzerConstants.PIP_INSTALL)
        return content.replace(DependencyAnalyzerConstants.PIP3_INSTALL_UPGRADE_FLAG, DependencyAnalyzerConstants.PIP3_INSTALL).replace(DependencyAnalyzerConstants.PIP3_INSTALL_U_FLAG, DependencyAnalyzerConstants.PIP3_INSTALL)
    if isinstance(content, list):
        new_list = []
        for c in content:
            new_list.append(remove_upgrade_option(c))
        return new_list
    if isinstance(content, dict):
        new_dict = {}
        for key in content:
            new_dict[key] = remove_upgrade_option(content[key])
        return new_dict
    return content


def modify_install_step(yaml_content_dict, stage_key, f_or_p, repo, add_before_pip=True):
    if stage_key in yaml_content_dict:
        stage_content = yaml_content_dict[stage_key]
        pip_install_found = False
        if not add_before_pip:
            pip_install_found = True
            stage_content = [DependencyAnalyzerConstants.PIP_INSTALL_PATCH.format(f_or_p, repo), stage_content]
        else:
            if DependencyAnalyzerConstants.PATCH_DEPENDENCY_FILE_NAME in stage_content:
                return True, yaml_content_dict
            if type(stage_content) and \
                (DependencyAnalyzerConstants.PIP_INSTALL in stage_content
                    or DependencyAnalyzerConstants.SETUP_PY in stage_content):
                pip_install_found = True
                stage_content = [DependencyAnalyzerConstants.PIP_INSTALL_PATCH.format(f_or_p, repo), stage_content]
            elif type(stage_content) and DependencyAnalyzerConstants.PIP3_INSTALL in stage_content:
                pip_install_found = True
                stage_content = [DependencyAnalyzerConstants.PIP3_INSTALL_PATCH.format(f_or_p, repo), stage_content]
            else:  #list
                for i in range(0, len(stage_content)):
                    if DependencyAnalyzerConstants.PIP_INSTALL in stage_content[i]\
                        or DependencyAnalyzerConstants.SETUP_PY in stage_content[i]:
                        pip_install_found = True
                        stage_content.insert(i, DependencyAnalyzerConstants.PIP_INSTALL_PATCH.format(f_or_p, repo))
                        break
                    elif DependencyAnalyzerConstants.PIP3_INSTALL in stage_content[i]:
                        pip_install_found = True
                        stage_content.insert(i, DependencyAnalyzerConstants.PIP3_INSTALL_PATCH.format(f_or_p, repo))
                        break
        if pip_install_found:
            yaml_content_dict[stage_key] = stage_content
            return True, yaml_content_dict
        else:
            return False, yaml_content_dict
    for key in yaml_content_dict:
        if isinstance(yaml_content_dict[key], dict):
            is_modified, modified_dict = modify_install_step(yaml_content_dict[key], stage_key, f_or_p, repo)
            if is_modified:
                yaml_content_dict[key] = modified_dict
                return True, yaml_content_dict
        elif isinstance(yaml_content_dict[key], list):
            for i in range(0, len(yaml_content_dict[key])):
                ele = yaml_content_dict[key][i]
                if isinstance(ele, dict):
                    is_modified, modified_dict = modify_install_step(ele, stage_key, f_or_p, repo)
                    if is_modified:
                        yaml_content_dict[key][i] = modified_dict
                        return True, yaml_content_dict
    return False, yaml_content_dict


def generate_and_prepare_build_script(f_or_p, cloned_repo_dir, repo, log_output_content):
    """ Generate new build script using travis-build to reflect changes made to .travis.yml
        Modify build script to prevent git code checkout during build """
    travis_command = DependencyAnalyzerConstants.TRAVIS_COMPILE_BUILD_SCRIPT.format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                        DependencyAnalyzerConstants.TRAVIS_BUILD_LOCATION))
    cd_command = DependencyAnalyzerConstants.CHANGE_DIR_CMD.format(cloned_repo_dir)
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(f'{cd_command}; {travis_command}')
    if not ok:
        log_output_content.append(stderr)
        log_output_content.append('Unable to generate travis build script')
        return False, log_output_content
    # prevent git checkout
    build_script_path = join(cloned_repo_dir, DependencyAnalyzerConstants.GENERATED_BUILD_SCRIPT_NAME)
    lines = []
    with open(build_script_path) as f:
        skip = False
        for line in f:
            if DependencyAnalyzerConstants.TRAVIS_START_GIT_CHECKOUT_CMD in line:
                skip = True
            elif DependencyAnalyzerConstants.TRAVIS_END_GIT_CHECKOUT_CMD in line:
                skip = False
                lines.append(DependencyAnalyzerConstants.TRAVIS_PREVENT_GIT_CHECKOUT_CMD.format(f_or_p, repo))
            else:
                if not skip:
                    lines.append(line)

    # Overwrite the original build script with the modified build script.
    with open(build_script_path, DependencyAnalyzerConstants.FILE_WRITE_MODE) as f2:
        for l in lines:
            f2.write(l)
    log_output_content.append('Successfully generated new build script')
    return True, log_output_content


def extract_from_file_name(log_file_name, artifact_dict):
    """ Extract info from BugCatcher log file name """
    image_tag = log_file_name.split(DependencyAnalyzerConstants.CHAR_STOP)[0]
    artifact = artifact_dict[image_tag]
    f_or_p = log_file_name.split(DependencyAnalyzerConstants.CHAR_STOP)[1]
    return artifact, f_or_p


def get_dependency_analyzer_results(input_files_path):
    """ Read results from csv output of Step 1 """
    content = []
    with open(join(input_files_path, DependencyAnalyzerConstants.LOG_DEP_ANALYZER_FILENM),
              DependencyAnalyzerConstants.FILE_READ_MODE) as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            content.append(row)
    return content


def cleanup(container_name=None, output_log_path=None, log_output_content=None, repo_dir=None):
    if output_log_path:
        append_output_log(output_log_path, log_output_content)
        log_output_content = []
    if container_name:
        SolverUtils.remove_docker_container(container_name)
    remove_intermediate_logs()
    #if repo_dir:
    #    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.REMOVE_DIR_CMD.format(repo_dir, DependencyAnalyzerConstants.CHAR_EMPTY))


def remove_intermediate_logs():
    _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.REMOVE_DIR_CMD.format(expanduser(DependencyAnalyzerConstants.STR_NOT_EQUALS_TILDE),
                                                                                                                   DependencyAnalyzerConstants.INTERMEDIATE_LOG_DIR))


if __name__ == '__main__':
    # python3 bugswarm_automate_iterative_dependency_solver.py 
    # -path <path to artifacts_dependency_broken.csv + artifacts.json>
    # -sourcecode <path to downloaded source code archives>
    # -intermediates <path to intermediate folder>
    main(sys.argv)
