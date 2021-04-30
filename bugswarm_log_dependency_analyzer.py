"""
Script to analyze build logs to identify dependency issues
"""
from os import mkdir, listdir, getcwd
from os.path import isfile, join, exists
import re
from multiprocessing import Pool, cpu_count
from functools import partial
import sys
import time
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from build_log_const import BuildLogConstants
from error_analyzer_utils import ErrorAnalyzerUtils
from reproduced_log_generator import ReproducedLogGenerator


""" Implementation of LogErrorAnalyzer for BugSwarm """


# path containing all build logs
log_files_path = ''
artifact_dict = {}


def main(args):
    start_time = time.time()
    global log_files_path, artifact_dict
    # if not DependencyAnalyzerUtils\
    #         .valid_input(args, DependencyAnalyzerConstants.LOG_DEP_ANALYZER_USAGE):
    #     return
    # else:
    log_files_path = args[2]
    orig_log_path = args[4]
    is_solver_run = False
    is_subset_run = False
    log_file_name = None
    if len(args) == 7:
        is_solver_run = True
        log_file_name = args[6]
    elif len(args) == 6:
        is_subset_run = True
    artifact_dict = DependencyAnalyzerUtils.get_artifact_dict(getcwd())
    filenames = []
    if not is_solver_run:
        generate_reproduced_logs(log_files_path, artifact_dict, is_subset_run)
        filenames = [f for f in listdir(log_files_path) if isfile(join(log_files_path, f))]
    else:
        filenames = [log_file_name]
    # all reproduced logs for passed builds
    repr_passed = []
    # all reproduced logs for failed builds
    repr_failed = []
    for f in filenames:
        if len(list(filter(f.startswith,
                           DependencyAnalyzerConstants.BUGSWARM_EXCLUSION_LIST))) != 0:
            continue
        if not is_python_artifact(f):
            continue
        if f.endswith(BuildLogConstants.PASSED_LOG_NAME_SUFFIX):
            repr_passed.append(f)
        elif f.endswith(BuildLogConstants.FAILED_LOG_NAME_SUFFIX):
            repr_failed.append(f)
    dep_issue_art = {}
    dep_issue_art.update(check_log(orig_log_path, repr_passed, BuildLogConstants.STR_PASSED))
    dep_issue_art.update(check_log(orig_log_path, repr_failed, BuildLogConstants.STR_FAILED))
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
                                            DependencyAnalyzerConstants.LOG_DEP_ANALYZER_FILENM)
    else:
        op_name = 'artifacts_dependency_broken_' + log_file_name.split()[0] + '.csv'
        DependencyAnalyzerUtils.write_to_csv(dep_issue_art_list,
                                            DependencyAnalyzerConstants.CSV_ARTIFACTS_BROKEN_HEADERS,
                                            op_name)


def generate_reproduced_logs(log_files_path, artifact_dict, is_subset_run):
    artifact_list = []
    if is_subset_run:
        for art in artifact_dict:
            if art in DependencyAnalyzerConstants.BUGSWARM_SUBSET_LIST:
                artifact_list.append(artifact_dict[art])
    else:
        for art in artifact_dict:
            exclude = False
            for str in DependencyAnalyzerConstants.BUGSWARM_EXCLUSION_LIST:
                if str in art:
                    exclude = True
                    break
            if exclude:
                continue
            if artifact_dict[art][DependencyAnalyzerConstants.LANGUAGE_KEY]\
                    != DependencyAnalyzerConstants.LANGUAGE_PYTHON:
                continue
            artifact_list.append(artifact_dict[art])

    with Pool(cpu_count()) as pool:
        results = pool.map(partial(ReproducedLogGenerator(1).start_log_gen,
                           f_or_p='failed',
                           output_path=log_files_path,
                           component_path=None), artifact_list)
    with Pool(cpu_count()) as pool:
        results = pool.map(partial(ReproducedLogGenerator(1).start_log_gen,
                           f_or_p='passed',
                           output_path=log_files_path,
                           component_path=None), artifact_list)


def check_log(orig_log_path, file_list, pass_fail):
    """ Parse each log, check for dependency errors, identify possible
    candidates """
    dep_issue_art = {}
    ansi_escape = re.compile(DependencyAnalyzerConstants.ANSI_ESCAPE_STR, re.M)
    for art in file_list:
        artname = art.split(DependencyAnalyzerConstants.CHAR_STOP)[0]
        content = []

        # read current log
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

        # Iterate over log lines
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
            lines_flagged, match_type_list, is_module_not_found, module_not_found_packages = ErrorAnalyzerUtils.add_matches(new_match_type, line, lines_flagged, idx, match_type_list, module_not_found_packages)

        # add nothing if build is successful
        if is_build_success:
            continue

        installed_packages = ErrorAnalyzerUtils.merge_same_installed_packages(installed_packages)

        # get orig log from travis
        orig_content = get_orig_log_contents(artifact_dict, artname, orig_log_path, pass_fail)
        if not orig_content:
            continue

        if len(match_type_list) > 0:
            # the line has matched at least one error pattern
            # checking if original logs had the same error
            orig_match_list = []
            for orig_line in orig_content:
                orig_match = DependencyAnalyzerUtils.check_matches(orig_line)
                if orig_match:
                    orig_match_list.append(orig_match)
            if len(list(set(match_type_list) - set(orig_match_list))) > 0:
                dep_issue_art[art] = {BuildLogConstants.KEY_LINES: lines_flagged,
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
                                            BuildLogConstants.KEY_FILE_NAME: '',
                                            'is_module_error': is_module_not_found}

            # identify possible candidates
            ErrorAnalyzerUtils.extract_packages_from_tracebacks(traceback_starts, dep_issue_art[art],
                                             content, orig_content,
                                             artifact_dict[artname][DependencyAnalyzerConstants.REPO_KEY])
        if module_not_found_packages:
            candidates = []
            if art in dep_issue_art:
                candidates = dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES]
            module_not_found_dep_issue_art = {}
            module_not_found_dep_issue_art[art] = {BuildLogConstants.KEY_LINES: module_not_found_packages,
                                              BuildLogConstants.KEY_POSSIBLE_CANDIDATES: candidates,
                                              BuildLogConstants.KEY_INSTALLED_PKGS: installed_packages,
                                              BuildLogConstants.KEY_FILE_NAME: DependencyAnalyzerConstants.CHAR_EMPTY,
                                              'is_module_error': True}
            ErrorAnalyzerUtils.localize_errors(module_not_found_dep_issue_art[art], content, True)
            if art not in dep_issue_art:
                dep_issue_art[art] = {BuildLogConstants.KEY_LINES: module_not_found_packages,
                                        BuildLogConstants.KEY_POSSIBLE_CANDIDATES: module_not_found_dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES],
                                        BuildLogConstants.KEY_INSTALLED_PKGS: installed_packages,
                                        BuildLogConstants.KEY_FILE_NAME: DependencyAnalyzerConstants.CHAR_EMPTY,
                                        'is_module_error': True}
            else:
                dep_issue_art[art][BuildLogConstants.KEY_LINES].update(module_not_found_packages)
                dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES] = module_not_found_dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES]

        if art not in dep_issue_art:
            continue
        if dep_issue_art[art] and not dep_issue_art[art][BuildLogConstants.KEY_POSSIBLE_CANDIDATES] and not dep_issue_art[art][BuildLogConstants.KEY_LINES]:
            del dep_issue_art[art]
            continue
    return dep_issue_art


def get_orig_log_contents(artifact_dict, artname, orig_log_path, pass_fail):
    """ Download original logs from TravisCI """
    orig_content = None
    if artname in artifact_dict:
        orig_file_name = DependencyAnalyzerConstants.ORIG_LOG_FILENM_PATTERN.format(artname, pass_fail)
        if isfile(join(orig_log_path, orig_file_name)):
            with open(join(orig_log_path, orig_file_name),
                        encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
                    orig_content = [x.strip() for x in f.readlines()]
        else:
            print('Original log file not available')
    else:
        print('{} not in artifacts.json'.format(artname))
    return orig_content


def is_python_artifact(file_name):
    """ Checking if log file belongs to python artifact """
    if file_name == DependencyAnalyzerConstants.ARTIFACTS_JSON_FILE_NAME:
        return False
    art_image_tag = file_name.split(DependencyAnalyzerConstants.CHAR_STOP)[0]
    try:
        if artifact_dict[art_image_tag][DependencyAnalyzerConstants.LANGUAGE_KEY]\
                == DependencyAnalyzerConstants.LANGUAGE_PYTHON:
            return True
    except KeyError:
        return False
    return False


if __name__ == '__main__':
    # python3 bugswarm_log_dependency_analyzer.py
    # -path <path to artifacts.json>
    # (optional) -solverrun <log file name>
    # (-optional) -subsetrun
    main(sys.argv)
