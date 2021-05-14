from error_patterns import inexact_pattern_list, error_pattern_list


class DependencyAnalyzerConstants:

    INEXACT_PATTERN_LIST = inexact_pattern_list
    ERROR_PATTERN_LIST = error_pattern_list

    # Header labels for Metrics.csv
    CSV_METRICS_HEADERS = ['Repository Name', 'Pass or Fail', 'Commit SHA', 'Image Tag',
                           '# Pip Unpinned Dependencies', 'Pip Unpinned Dependency List',
                           '# Pip Pinned Dependencies', 'Pip Pinned Dependency List',
                           '# Apt Unpinned Dependencies', 'Apt Unpinned Dependency List',
                           '# Apt Pinned Dependencies', 'Apt Pinned Dependency List']

    # Header labels for artifacts_dependency_broken.csv
    CSV_ARTIFACTS_BROKEN_HEADERS = ['Reproduced Log File Name', 'Error Line Flagged', 'Possible Candidates', 'Requirements File']
    COMPARE_ARTIFACTS_BROKEN_HEADERS = ['Reproduced Log File Name', 'NEW Error Line Flagged', 'NEW Possible Candidates',
                                         'NEW Requirements File', 'ORIG Error Line Flagged', 'ORIG Possible Candidates']

    # Header labels for IterativeDependencySolver output
    BUGSWARM_CSV_SOLVER_RESULTS_HEADERS = ['Log File Name', 'Final Patch', 'Fix Outcome', 'Analyzer Output', 'Time in s', '# Iterations']
    COMPARE_BUGSWARM_CSV_SOLVER_RESULTS_HEADERS = ['Log File Name', 'NEW Final Patch', 'NEW Fix Outcome', 'NEW Analyzer Output',
                                                   'NEW Time in s', 'OLD Final Patch', 'OLD Fix Outcome', 'OLD Analyzer Output', 'OLD Time in s']
    BUGSINPY_CSV_SOLVER_RESULTS_HEADERS = ['Log File Name', 'Final Patch', 'Fix Outcome', 'Time in s', '# Iterations']
    COMPARE_BUGSINPY_CSV_SOLVER_RESULTS_HEADERS = ['Log File Name', 'NEW Final Patch', 'NEW Fix Outcome',
                                                   'OLD Time in s', 'OLD Final Patch', 'OLD Fix Outcome', 'OLD Time in s']

    # Delimiter in Error Line Flagged column in artifacts_dependency_broken.csv
    ERROR_LINE_DELIMITER = '<DELIM>'

    # Usage metrics_finder.py
    METRICS_USAGE = 'Usage: python3 metrics_finder.py -path <path-to-directory>'

    # file name for metrics_finder.py output
    METRICS_OUTPUT_FILENM = 'metrics.csv'

    # Usage log_dependency_analyzer.py
    LOG_DEP_ANALYZER_USAGE = 'Usage: python3 log_dependency_analyzer.py -path <path-to-build-logs-directory>'

    # Usage automate_iterative_dependency_solve.py
    ITERATIVE_DEP_SOLVE_USAGE = 'Usage: python3 automate_iterative_dependency_solve.py \
            -path <path to artifacts_dependency_broken.csv + artifacts.json> \
            -component <path to bugswarm component> \
            -intermediate <path to intermediates folder>'

    # file name for log_dependency_analyzer.py output
    LOG_DEP_ANALYZER_FILENM = 'artifacts_dependency_broken.csv'

    # Usage docker_travis_extract_script.py
    DOCKER_EXTRACT_USAGE = 'Usage: python3 docker_travis_extract_script.py -path <path-to-artifact-list-directory> -output <path-to-output-directory> <optional-arguments> \n Optional: -all-artifacts'

    # evaluate_logs_pinned.py usage
    LOG_DEP_EVAL_USAGE = 'Usage: python3 evaluate_logs_pinned.py -path <path-to-log-files>'

    # artifacts.json file name
    ARTIFACTS_JSON_FILE_NAME = 'artifacts.json'

    # language names
    LANGUAGE_PYTHON = 'Python'
    LANGUAGE_PYTHON_LOWERCASE = 'python'

    # artifacts.json keys
    LANGUAGE_KEY = 'lang'
    FAILED_JOB_KEY = 'failed_job'
    PASSED_JOB_KEY = 'passed_job'
    JOB_ID_KEY = 'job_id'
    BUILD_ID_KEY = 'build_id'
    REPO_KEY = 'repo'
    PR_NUM_KEY = 'pr_num'
    JOB_KEY_SUFFIX = '_job'
    TRIGGER_SHA_KEY = 'trigger_sha'
    IMAGE_TAG_KEY = 'image_tag'
    JOB_KEY = '{}_job'
    COMMITTED_AT_KEY = 'committed_at'
    DIFF_URL_KEY = 'diff_url'

    # patch keys
    NAME_KEY = 'name'
    APPLIED_KEY = 'applied'
    INCLUDED_KEY = 'included'
    VERSION_KEY = 'version'

    # ANALYZER ATTRIBUTE KEYS
    ATTR_KEY = 'attr'
    LOG_STATUS_KEY = 'tr_log_status'
    LOG_TESTS_RUN_KEY = 'tr_log_bool_tests_ran'
    LOG_TESTS_FAILED_KEY = 'tr_log_num_tests_failed'

    # CANDIDATE KEYS
    CANDIDATE_NAME_KEY = '_name'
    CANDIDATE_VERSION_CONSTRAINT_KEY = '_version_constraints'

    # reproducer file and directory naming conventions
    FIRST_RUN_REPRO_DIRECTORY_SUFFIX = '_run1'
    ORIG_LOG_SRC_DIR = 'reproducer/intermediates/orig_logs'
    ORIG_LOG_FILE_NAME_SUFFIX = '-orig.log'
    REPRO_LOG_SRC_DIR = 'reproducer/output/tasks'
    REPRO_OUTPUT_DIR = 'reproducer/output'
    REPRO_INPUT_DIR = 'reproducer/input'
    REPRO_INTERMEDIATES_DIR = 'reproducer/intermediates'
    ORIG_LOG_FILENM_PATTERN = '{}.{}.orig.log'

    # created output log dir names
    DIR_WO_DEP_SOLVER = 'wo_dep_solver'
    DIR_W_DEP_SOLVER = 'w_dep_solver'

    # repro console log file names
    WO_DEP_SOLVER_CONSOLE_LOG_FILE = 'repro_log_wo_dep_solver.txt'
    W_DEP_SOLVER_CONSOLE_LOG_FILE = 'repro_log_w_dep_solver.txt'

    # Reproducer command for run_reproduce_pair.sh
    REPRODUCER_COMMAND = 'bash {}/run_reproduce_pair.sh -r {} -f {} -p {} -t 2 -c {} --automated true > repro_log_wo_dep_solver.txt'
    REPRODUCER_WITH_DEPENDENCY_SOLVER_COMMAND = 'bash {}/run_reproduce_pair.sh -r {} -f {} -p {} -t 2 -c {} --automated true --dep-solver true > repro_log_w_dep_solver.txt'

    # Regex to check reproducibility status
    REPRODUCIBLE_PATTERN = r'job pair reproducibility: '

    # automate_reproducer_run.py usage
    AUTOMATE_REPRODUCER_USAGE = 'Usage: python3 automate_reproducer_run.py -path <path-artifacts.json-metrics.csv> -output <path-to-copy-all-logs> -component <path-to-BugSwarm-components>'

    # automate_reproducer_run.py output file names
    REPRODUCER_EVAL_FILENAME = 'reproducer_evaluation.csv'
    FAILED_ARTIFACTS_FILENAME = 'failed_artifacts.txt'

    # automate_reproducer_run.py output csv headers
    CSV_REPRODUCER_EVAL_HEADERS = ['Repository Name', 'Image tag', 'Status w/o dependency solver',
                                   'Status with dependency solver', '# Lines in failed original logs',
                                   '# Lines in failed reproduced logs w/o dependency solver',
                                   '# Lines in failed reproduced logs w/ dependency solver',
                                   '# Lines in passed original logs',
                                   '# Lines in passed reproduced logs w/o dependency solver',
                                   '# Lines in passed reproduced logs w/ dependency solver']

    # Reproducer log analysis strings
    ANSI_ESCAPE_STR = r'\x1B[@-_][0-?]*[ -/]*[@-~]'
    SPECIFIERS = ['==', '~=', '!=', '<=', '>=', '<', '>', '===']
    REQUIRED_LOG_PATTERN = 'Collecting'
    DISCARD_LOG_PATTERN = ['http', 'git']

    # evaluate_logs_pinned.py output csv headers
    CSV_LOG_DEP_EVAL_HEADERS = ['Image Tag', '# Pinned in Original', 'Pinned in Original',
                                '# Unpinned in Original', 'Unpinned in Original',
                                '# Pinned w/o dep-solver', 'Pinned w/o dep-solver',
                                '# Unpinned w/o dep-solver', 'Unpinned w/o dep-solver',
                                '# Pinned w dep-solver', 'Pinned w dep-solver',
                                '# Unpinned w dep-solver', 'Unpinned w dep-solver',
                                'Contains Dependency Errors',
                                '# Diff in Pinned from original',
                                '# Same version pinned as original w/o dep-solver',
                                'Packages with same version pinned as original w/o dep-solver',
                                '# Same version pinned as original w/ dep-solver',
                                'Packages with same version pinned as original w/ dep-solver']

    # eval_logs_pinned.py output csv name
    CSV_LOG_DEP_EVAL_FILE_NAME = 'logs_pinned.csv'

    # characters
    CHAR_STOP = '.'
    CHAR_COMMA = ','
    CHAR_EMPTY = ''
    CHAR_SPACE = ' '
    CHAR_NEW_LINE = '\n'
    CHAR_DOUBLE_QUOTE = '"'
    CHAR_SINGLE_QUOTE = "'"
    CHAR_SLASH = '/'
    CHAR_HYPHEN = '-'
    CHAR_UNDERSCORE = '_'
    CHAR_OPEN_PARENTHESIS = '('
    CHAR_CLOSE_PARENTHESIS = ')'
    CHAR_TILDE = '~'
    CHAR_GREATER = '>'
    CHAR_LESSER = '<'
    CHAR_SEMI_COLON = ';'

    # strings
    STR_ENCODING_UTF8 = 'utf-8'
    STR_EQUALS = '=='
    STR_NOT_EQUALS = '!='
    STR_NOT_EQUALS_TILDE = '~='
    STR_GREATER_EQUALS = '>='
    STR_LESSER_EQUALS = '<='
    STR_REPRODUCIBLE = 'Reproducible'
    STR_PASSED = 'passed'
    STR_FAILED = 'failed'
    STR_PASSED_VERSION = '1'
    STR_FAILED_VERSION = '0'
    STR_TWO_DOTS = '..'

    # artifacts that no longer have pairs
    BUGSWARM_EXCLUSION_LIST = ['terasoluna', 'getnikola', 'Cal-CS-61A-Staff', 'jacebrowning']
    BUGSINPY_EXCLUSION_LIST = ['fastapi', 'httpie', 'keras', 'luigi', 'thefuck', 'youtube-dl']

    # subset list
    BUGSWARM_SUBSET_LIST = ['scikit-learn-scikit-learn-424798793',
                            'numpy-numpy-105433444',
                            'Unidata-netcdf4-python-356451404',
                            'zimmerman-zimmerman-OIPA-91222724',
                            'Charcoal-SE-SmokeDetector-398545910',
                            'paramiko-paramiko-299944105',
                            'getslash-slash-319194091',
                            'joblib-joblib-299740779',
                            'asciimoo-searx-305344714',
                            'biolab-orange3-198073997',
                            'bwhmather-verktyg-110761266',
                            'byteweaver-django-coupons-89457803']
    #['numpy-numpy-100031174', 'Unidata-netcdf4-python-356451404',
     #                       'zimmerman-zimmerman-OIPA-91222724', 'paramiko-paramiko-137019227','scikit-learn-scikit-learn-424798793', 'marshallward-f90nml-313386864','hivesolutions-appier-380817820', 'numpy-numpy-105433444',
      #                      'GNS3-gns3-server-247114372', 'indico-indico-337640094']
    BUGSINPY_SUBSET_LIST = ['black_10', 'pandas_1', 'matplotlib_1', 'scrapy_36',
                            'sanic_5', 'pandas_105', 'scrapy_1', 'black_11',
                            'black_12', 'tornado_10', 'sanic_1', 'sanic_2']

    # csv cell capacity
    INT_CSV_CELL_MAX_LIMIT = 30000

    # File extension
    PYTHON_FILE_EXT = '.py'
    LOG_FILE_EXT = '.log'
    CSV_FILE_EXT = '.csv'

    # new travis build script name
    GENERATED_BUILD_SCRIPT_NAME = 'test.sh'

    # travis build success message
    BUILD_SUCCESS_LOG = 'Your build exited with 0'

    # bugswarm client sandbox name
    BUGSWARM_CLIENT_SANDBOX = 'bugswarm-sandbox'

    # Docker commands for iterative dependency patch application
    DOCKER_EXEC_SCRIPT_CMD = 'sudo docker exec {} python apply_fix_to_container.py {} {} {}'
    DOCKER_LOG_CP_CMD = 'sudo docker cp {}:/home/travis/log-{}.log {}'
    DOCKER_RUN_IMAGE_CMD = 'sudo docker run -t -d --name {} bugswarm/images:{} /bin/sh'
    DOCKER_GET_CONTAINER_ID_CMD = 'sudo docker ps -a --format "{{.ID}}" --filter "name='
    DOCKER_COPY_SCRIPT_CMD = 'sudo docker cp apply_fix_to_container.py {}:/'
    DOCKER_COPY_BUILD_SCRIPT_CMD = 'sudo docker cp {} {}:/usr/local/bin/run_{}.sh'
    DOCKER_COPY_SOURCE_CODE_CMD = 'sudo docker cp {} {}:/home/travis/build/{}/{}'
    DOCKER_REMOVE_CONTAINER = 'sudo docker rm --force {}'
    DOCKER_COPY_SOURCE_CODE_CMD = 'sudo docker cp {}/. {}:/home/travis/build/{}/{}'
    DOCKER_REMOVE_CONTAINER = 'sudo docker rm --force /{}'
    DOCKER_RUN_AS_ROOT_CMD = 'sudo docker run -t -d --name {} -u root {} /bin/bash'
    DOCKER_CP_HOME_CMD = 'sudo docker cp {} {}:/home'
    DOCKER_HOME_CHANGE_PERM_CMD = 'sudo docker exec -u root {} /bin/sh -c "chmod -R 777 /home/{}"'
    DOCKER_PIP_CHANGE_PERM_CMD = 'sudo docker exec -u root {} /bin/sh -c "chmod -R 777 /home/docker"'
    DOCKER_EXEC_BUILD_JOB_CMD = 'sudo docker exec -u root {} /bin/sh -c "cd /home/{} && ./test.sh > log-output.log 2>&1"'
    DOCKER_CP_BUILD_LOG_CMD = 'sudo docker cp {}:/home/{}/log-output.log {}/{}_{}_{}.log'

    # Terminal commands
    TRAVIS_BUILD_LOCATION = '.travis/travis-build/bin/travis'
    TRAVIS_COMPILE_BUILD_SCRIPT = '{} compile > test.sh'
    CHANGE_DIR_CMD = 'cd {}'
    REMOVE_DIR_CMD = 'rm -rf {}/{}'
    CREATE_DIR_CMD = 'sudo mkdir {}/{}'
    SUDO_MKDIR = 'sudo mkdir {}'
    COPY_FILE_CMD = 'cp {} {}'
    BUGSWARM_RUN_LOG_ANALYZER = 'python3 bugswarm_log_dependency_analyzer.py -path {} -originallogs ~/PyDFix/orig_log_bugswarm -solverrun {}'
    BUGSINPY_RUN_LOG_ANALYZER = 'python3 bugsinpy_log_dependency_analyzer.py -path {} -originallogs {} -component {} -solverrun {}'
    CHANGE_PERMISSION_CMD = 'sudo chmod -R 777 {}'
    COPY_BUGSWARM_SANDBOX_LOG = 'cp ~/bugswarm-sandbox/{}_{}.log {}'
    SUDO_RM_CMD = 'sudo rm {}'
    SUDO_RM_RF_CMD = 'sudo rm -rf {}'
    GIT_CLONE_CMD = 'mkdir {} && cd {} && git clone {}.git'
    GIT_RESET_HARD_CMD = 'cd {} && git reset --hard {}'

    # File input modes
    FILE_READ_MODE = 'r'
    FILE_WRITE_MODE = 'w'
    FILE_WRITE_PLUS_MODE = 'w+'
    FILE_ACCESS_MODE = 'a'
    ZIPFILE_ACCESS_MODE = 'wb'

    # Directory Locations
    TRAVIS_BUILD_LOCATION = '.travis/travis-build/bin/travis'
    REPRODUCER_WORKSPACE_DIR_LOCN = 'reproducer/intermediates/workspace'
    INTERMEDIATE_LOG_DIR = 'intermediate_log'

    # Patch file names
    PATCH_DEPENDENCY_FILE_NAME = 'patch_requirements.txt'
    PATCH_COMBO_FILE_NAME = 'patch_combos.txt'
    TRAVIS_YAML_FILE_NAME = '.travis.yml'
    INTERMEDIATE_LOG_FILE_NAME = 'log-{}.log'

    # PYPI JSON API
    PYPI_PKG_HISTORY_URL = 'https://pypi.org/pypi/{}/json'
    PYPI_VERSION_HISTORY_URL = 'https://pypi.org/pypi/{}/{}/json'

    # Travis stages
    TRAVIS_BEFORE_INSTALL = 'before_install'
    TRAVIS_INSTALL = 'install'
    TRAVIS_SCRIPT = 'script'
    TRAVIS_LANGUAGE = 'language'
    TRAVIS_ENV = 'env'

    # installs
    PIP_INSTALL = 'pip install'
    PIP_INSTALL_UPGRADE_FLAG = 'pip install --upgrade'
    PIP_INSTALL_U_FLAG = 'pip install -U'
    PIP3_INSTALL = 'pip3 install'
    PIP3_INSTALL_UPGRADE_FLAG = 'pip install --upgrade'
    PIP3_INSTALL_U_FLAG = 'pip install -U'
    PIP_INSTALL_PATCH = 'pip install -r /home/travis/build/{}/{}/patch_requirements.txt --no-deps'
    PIP3_INSTALL_PATCH = 'pip3 install -r /home/travis/build/{}/{}/patch_requirements.txt --no-deps'
    SETUP_PY = 'setup.py'

    # travis build script
    TRAVIS_PREVENT_GIT_CHECKOUT_CMD = r'travis_cmd cd\ {}/{} --assert --echo\n'
    TRAVIS_START_GIT_CHECKOUT_CMD = 'start git.checkout'
    TRAVIS_END_GIT_CHECKOUT_CMD = 'travis_fold end git.checkout'

    # PyPI JSON API response keys
    PYPI_API_RELEASES_KEY = 'releases'
    PYPI_API_UPLOAD_TIME_KEY = 'upload_time'

    # BugsInPy Filenames
    ORIG_FILE_NAME_FORMAT = '{}_{}_{}_orig.log'

    # Run Directory
    ITER_RUN_DIR_NAME = 'run-{}'
    ARTIFACT_DIR = '{}_{}'
    LOG_FILE_NM_PATTERN = '{}_{}.log'

    # BugsInPy dirs
    PROJECTS_DIR = 'projects'
    BUGS_DIR = 'bugs'

    # BugsInPy info files
    BUG_INFO_FILENM = 'bug.info'
    PROJECT_INFO_FILE_NAME = 'project.info'
    SETUP_SH_FILE_NAME = 'setup.sh'
    RUN_TEST_SH_FILE_NAME = 'run_test.sh'

    # BugsInPy info file strings
    INFO_PYTHON_VERSION = 'python_version='
    INFO_BUGGY_COMMIT = 'buggy_commit_id='
    INFO_FIXED_COMMIT = 'fixed_commit_id='
    INFO_GIT_URL = 'github_url='
    INFO_TEST_FILE = 'test_file='
    INFO_PYTHON_PATH = 'pythonpath='


    # Python versions
    PYTHON_3_8_3 = '3.8.3'
    PYTHON_3_8_1 = '3.8.1'
    PYTHON_3_7_7 = '3.7.7'
    PYTHON_3_7_0 = '3.7.0'
    PYTHON_3_6_9 = '3.6.9'

    # PYTHON DOCKER IMAGE NAMES
    PYTHON_3_8_3_IMAGE_NAME = 'suchita94/bugsinpy-container-py383:latest'
    PYTHON_3_8_1_IMAGE_NAME = 'suchita94/bugsinpy-container-py381:latest'
    PYTHON_3_7_7_IMAGE_NAME = 'suchita94/bugsinpy-container-py377:latest'
    PYTHON_3_7_0_IMAGE_NAME = 'suchita94/bugsinpy-container-py370:latest'
    PYTHON_3_6_9_IMAGE_NAME = 'suchita94/bugsinpy-container-py369:latest'

    # Intermediate log file names
    OUTPUT_LOG = 'output-log.log'

    # GitHub constants
    GITHUB_USER_NAME =
    GITHUB_AUTH_TOKEN =
    GITHUB_URL = 'https://github.com/'
    GITHUB_COMMITS_API_URL = 'https://api.github.com/repos/{}/commits/{}'
    GITHUB_ARCHIVE_API_URL = 'https://api.github.com/repos/{}/zipball/{}'
    GITHUB_JSON_COMMIT_KEY = 'commit'
