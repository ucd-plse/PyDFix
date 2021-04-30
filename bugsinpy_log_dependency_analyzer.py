"""
Script to analyze build logs to identify dependency issues
"""
from os import listdir
from os.path import isfile, join, isdir
import re
import sys
import os
import time
from multiprocessing import Pool, cpu_count
from functools import partial
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from build_log_const import BuildLogConstants
from error_analyzer_utils import ErrorAnalyzerUtils
from original_log_generator import OriginalLogGenerator
from reproduced_log_generator import ReproducedLogGenerator


""" Implementation of LogErrorAnalyzer for BugsInPy """


# path containing all build logs
log_files_path = ''


def main(args):
    start_time = time.time()
    global log_files_path
    log_files_path = args[2]
    original_log_files_path = args[4]
    component_path = args[6]
    is_solver_run = False
    is_subset_run = False
    if len(args) == 9:
        is_solver_run = True
        log_file_nm = args[8]
    elif len(args) == 8:
        is_subset_run = True

    if is_solver_run:
        filenames = [log_file_nm]
    else:
        failed_art_list = []
        passed_art_list = []
        if is_subset_run:
            for proj_bug in DependencyAnalyzerConstants.BUGSINPY_SUBSET_LIST:
                proj = proj_bug.split('_')[0]
                bug = proj_bug.split('_')[1]
                if not isfile(join(log_files_path, '{}_{}_{}.log'.format(proj, bug, '0'))):
                    failed_art_list.append('{}_{}_{}'.format(proj, bug, '0'))
                if not isfile(join(log_files_path, '{}_{}_{}.log'.format(proj, bug, '1'))):
                    passed_art_list.append('{}_{}_{}'.format(proj, bug, '1'))

        else:
            proj_list = os.listdir(join(component_path, 'projects'))
            for proj in proj_list:
                if proj in DependencyAnalyzerConstants.BUGSINPY_EXCLUSION_LIST:
                    continue
                if not isdir(join(component_path, 'projects', proj)):
                    continue
                bugs_list = os.listdir(join(component_path, 'projects', proj, 'bugs'))
                for bug in bugs_list:
                    if proj == 'matplotlib' and bug != '1':
                        continue
                    if not isdir(join(component_path, 'projects', proj, 'bugs', bug)):
                        continue
                    if not isfile(join(log_files_path, '{}_{}_{}.log'.format(proj, bug, '0'))):
                        failed_art_list.append('{}_{}_{}'.format(proj, bug, '0'))
                    if not isfile(join(log_files_path, '{}_{}_{}.log'.format(proj, bug, '1'))):
                        passed_art_list.append('{}_{}_{}'.format(proj, bug, '1'))
        with Pool(cpu_count()) as pool:
            results = pool.map(partial(ReproducedLogGenerator(2).start_log_gen,
                            f_or_p='failed',
                            output_path=log_files_path,
                            component_path=component_path), failed_art_list)
        with Pool(cpu_count()) as pool:
            results = pool.map(partial(ReproducedLogGenerator(2).start_log_gen,
                            f_or_p='passed',
                            output_path=log_files_path,
                            component_path=component_path), passed_art_list)

        filenames = [f for f in listdir(log_files_path) if isfile(join(log_files_path, f)) and f.endswith(DependencyAnalyzerConstants.LOG_FILE_EXT)]
    # all reproduced logs for passed builds
    repr_passed = []
    # all reproduced logs for failed builds
    repr_failed = []
    for f in filenames:
        if len(list(filter(f.startswith,
                           DependencyAnalyzerConstants.BUGSINPY_EXCLUSION_LIST))) != 0:
            continue
        repr_failed.append(f)
    dep_issue_art = {}
    dep_issue_art.update(check_log(repr_passed, BuildLogConstants.STR_PASSED, original_log_files_path, component_path))
    dep_issue_art.update(check_log(repr_failed, BuildLogConstants.STR_FAILED, original_log_files_path, component_path))
    end_time = time.time()
    print('==========**** LogErrorAnalyzer FINAL OUTPUT ****==========')
    if len(filenames) == 0:
        print('No reproduced logs generated to identify')
    else:
        print('Number of builds identified: {}'.format(len(dep_issue_art)))
        print('Number of builds available: {}'.format(len(filenames)))
        print('Percentage Identification: {}'.format(len(dep_issue_art)*100/len(filenames)))
        print('Total Runtime: {} minutes'.format((end_time - start_time)/60))
    print('==========**** END OF OUTPUT ****==========')
    dep_issue_art_list = ErrorAnalyzerUtils.convert_dict_to_list(dep_issue_art)
    if not is_solver_run:
        DependencyAnalyzerUtils.write_to_csv(dep_issue_art_list,
                                             DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                             'bugsinpy_artifacts_dependency_broken.csv')
    else:
        op_name = 'bugsinpy_artifacts_dependency_broken_' + log_file_nm + DependencyAnalyzerConstants.CSV_FILE_EXT
        DependencyAnalyzerUtils.write_to_csv(dep_issue_art_list,
                                             DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                             op_name)


def check_log(file_list, pass_fail, original_log_files_path, component_path):
    """ Parse each log, check for dependency errors, identify possible
        candidates """
    dep_issue_art = {}
    ansi_escape = re.compile(DependencyAnalyzerConstants.ANSI_ESCAPE_STR, re.M)
    for art in file_list:
        print('Processing {}...'.format(art))
        repo_name = art.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[0]
        bug_id = art.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[1]
        version = art.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[2].split(DependencyAnalyzerConstants.CHAR_STOP)[0]
        if version == DependencyAnalyzerConstants.STR_PASSED_VERSION:
            pass_fail = DependencyAnalyzerConstants.STR_PASSED
        else:
            pass_fail = DependencyAnalyzerConstants.STR_FAILED
        content = []
        # Read log
        with open(join(log_files_path, art),
                  encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
            content = [x.strip() for x in f.readlines()]
        match_type_list = []
        lines_flagged = {}
        traceback_starts = {}
        installed_packages = []
        last_identified_package = {}
        dep_file_names = []
        is_build_success = False
        is_module_not_found = False
        module_not_found_packages = {}

        # Start iterating over log lines
        for idx in range(0, len(content)):
            line = content[idx]
            line = ansi_escape.sub(DependencyAnalyzerConstants.CHAR_EMPTY, line)

            # check if line shows build success for passed builds
            if pass_fail == BuildLogConstants.STR_PASSED and DependencyAnalyzerConstants.BUILD_SUCCESS_LOG in line:
                is_build_success = True
                break

            # check if this line is collecting a package
            if line.startswith(BuildLogConstants.LOG_STR_COLLECTING):
                if idx < len(content) - 1:
                    last_identified_package, file_nm = ErrorAnalyzerUtils.get_package_info(line, content[idx + 1])
                else:
                    last_identified_package, file_nm = ErrorAnalyzerUtils.get_package_info(line)
                if not last_identified_package:
                    continue
                installed_packages.append(last_identified_package)
                if file_nm:
                    dep_file_names.append(file_nm.split(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)[0].strip())
                continue
            elif line.startswith(BuildLogConstants.LOG_STR_SEARCHING):
                last_identified_package, file_nm = ErrorAnalyzerUtils.get_package_info(line, content[idx + 3])
                if not last_identified_package:
                    continue
                installed_packages.append(last_identified_package)
                if file_nm:
                    dep_file_names.append(file_nm.split(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)[0].strip())
                continue
            elif line.startswith(BuildLogConstants.LOG_STR_REQUIREMENT_SATISFIED):
                last_identified_package, file_nm = ErrorAnalyzerUtils.get_package_info(line, line)
                if not last_identified_package:
                    continue
                installed_packages.append(last_identified_package)
                if file_nm:
                    dep_file_names.append(file_nm.split(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)[0].strip())
                continue
            elif line.startswith(BuildLogConstants.LOG_STR_DOWNLOADING)\
                    or line.startswith(BuildLogConstants.LOG_STR_BEST_MATCH):
                continue

            # checking if this is the start of a traceback
            traceback_starts, start_traceback = ErrorAnalyzerUtils.check_if_traceback(line, traceback_starts, idx)
            if start_traceback:
                continue

            # checking if this line in the reproduced log matches any of the known error patterns
            new_match_type = DependencyAnalyzerUtils.check_matches(line)
            lines_flagged, match_type_list, is_module_not_found, module_not_found_packages = ErrorAnalyzerUtils.add_matches(new_match_type,
                                                                                                 line,
                                                                                                 lines_flagged,
                                                                                                 idx,
                                                                                                 match_type_list,
                                                                                                 module_not_found_packages)
        # add nothing if build is successful
        if is_build_success:
            continue

        installed_packages = ErrorAnalyzerUtils.merge_same_installed_packages(installed_packages)
        # Check if the error exists in orig logs
        new_lines_flagged, orig_content = check_in_original_logs(lines_flagged,
                                                                 original_log_files_path,
                                                                 repo_name, bug_id, version,
                                                                 component_path)
        module_not_found_packages, orig_content = check_in_original_logs(module_not_found_packages,
                                                                 original_log_files_path,
                                                                 repo_name, bug_id, version,
                                                                 component_path)
        if new_lines_flagged:
            dep_issue_art[art] = {BuildLogConstants.KEY_LINES: new_lines_flagged,
                                        BuildLogConstants.KEY_POSSIBLE_CANDIDATES: [],
                                        BuildLogConstants.KEY_INSTALLED_PKGS: installed_packages,
                                        BuildLogConstants.KEY_FILE_NAME: dep_file_names,
                                        'is_module_error': is_module_not_found}

            # identify possible candidates
            ErrorAnalyzerUtils.localize_errors(dep_issue_art[art], content)
            if last_identified_package:
                ErrorAnalyzerUtils.add_if_not_added(dep_issue_art[art], last_identified_package.name)

        if traceback_starts:
            if art not in dep_issue_art:
                dep_issue_art[art] = {BuildLogConstants.KEY_LINES: {},
                                            BuildLogConstants.KEY_POSSIBLE_CANDIDATES: [],
                                            BuildLogConstants.KEY_INSTALLED_PKGS: installed_packages,
                                            BuildLogConstants.KEY_FILE_NAME: DependencyAnalyzerConstants.CHAR_EMPTY,
                                            'is_module_error': is_module_not_found}

            # identify possible candidates
            ErrorAnalyzerUtils.extract_packages_from_tracebacks(traceback_starts, dep_issue_art[art],
                                             content, orig_content,
                                             art.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[0].strip())

        if module_not_found_packages:
            module_not_found_dep_issue_art = {}
            candidates = []
            if art in dep_issue_art:
                candidates = dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES]
            module_not_found_dep_issue_art[art] = {BuildLogConstants.KEY_LINES: module_not_found_packages,
                                        BuildLogConstants.KEY_POSSIBLE_CANDIDATES: candidates,
                                        BuildLogConstants.KEY_INSTALLED_PKGS: installed_packages,
                                        BuildLogConstants.KEY_FILE_NAME: DependencyAnalyzerConstants.CHAR_EMPTY,
                                        'is_module_error': True}
            ErrorAnalyzerUtils.localize_errors(module_not_found_dep_issue_art[art], content, True)
            if art not in dep_issue_art:

                dep_issue_art[art] = {BuildLogConstants.KEY_LINES: module_not_found_packages,
                                        BuildLogConstants.KEY_POSSIBLE_CANDIDATES: module_not_found_dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES],
                                        BuildLogConstants.KEY_INSTALLED_PKGS: module_not_found_dep_issue_art[art][BuildLogConstants.KEY_INSTALLED_PKGS],
                                        BuildLogConstants.KEY_FILE_NAME: DependencyAnalyzerConstants.CHAR_EMPTY,
                                        'is_module_error': True}
            else:
                dep_issue_art[art][BuildLogConstants.KEY_LINES].update(module_not_found_dep_issue_art[art][BuildLogConstants.KEY_LINES])
                dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES] = module_not_found_dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES]



        if art not in dep_issue_art:
            continue
        if dep_issue_art[art] and not dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES]\
            and not dep_issue_art[art][BuildLogConstants.KEY_LINES]:
            del dep_issue_art[art]
            continue

    return dep_issue_art


def check_in_original_logs(lines_flagged, original_log_files_path, repo_name, bug_id, version, component_path):
    # if not lines_flagged:
    #    return False, None
    original_file_nm = DependencyAnalyzerConstants.ORIG_FILE_NAME_FORMAT.format(repo_name, str(bug_id), str(version))
    orig_content = None
    if isfile(join(original_log_files_path, original_file_nm)):
        with open(join(original_log_files_path, original_file_nm)) as f:
            orig_content = [x.strip() for x in f.readlines()]
    else:
        # Generate original log
        orig_log_gen = OriginalLogGenerator(2)
        orig_content = orig_log_gen.start_log_gen('{}_{}_{}'.format(repo_name, bug_id, version), original_log_files_path, None, component_path)
    if not orig_content:
        return False, None
    orig_match_list = []
    orig_lines_flagged = {}

    # Iterate over original log lines
    for idx in range(0, len(orig_content)):
        orig_line = orig_content[idx]
        orig_match = DependencyAnalyzerUtils.check_matches(orig_line)
        if orig_match:
            orig_match_list.append(orig_match)
            orig_lines_flagged[idx] = {BuildLogConstants.KEY_LINE: orig_line.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE,
                                                                                     DependencyAnalyzerConstants.CHAR_EMPTY),
                                       BuildLogConstants.KEY_TYPE: orig_match}

    new_lines_flagged = {}

    # check against current log's identified lines
    for new_id in lines_flagged:
        found = False
        for orig_id in orig_lines_flagged:
            if orig_lines_flagged[orig_id][BuildLogConstants.KEY_TYPE] == lines_flagged[new_id][BuildLogConstants.KEY_TYPE]\
                and orig_lines_flagged[orig_id][BuildLogConstants.KEY_LINE] == lines_flagged[new_id][BuildLogConstants.KEY_LINE]:
                found = True
        if not found:
            new_lines_flagged[new_id] = lines_flagged[new_id]

    return new_lines_flagged, orig_content


if __name__ == '__main__':
    # USAGE: python3 bugsinpy_log_dependency_analyzer.py
    # -path <path to reproduced logs>
    # -originallogs <path to original logs>
    # -component <path to BugsInPy>
    # (optional) -solverrun <log file name>
    # (optional) -subsetrun
    main(sys.argv)
