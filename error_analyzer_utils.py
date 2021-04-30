import json
import re
from dependency_analyzer_const import DependencyAnalyzerConstants
from build_log_const import BuildLogConstants
from error_type import ErrorType
from package_info import PackageInfo


class ErrorAnalyzerUtils:
    @staticmethod
    def convert_dict_to_list(dep_issue_art):
        dep_issue_art_list = []
        for key in dep_issue_art:
            new_list = []
            new_list.append(key)
            new_list.append(DependencyAnalyzerConstants.ERROR_LINE_DELIMITER.join(map(lambda x: x[BuildLogConstants.KEY_LINE],
                                        dep_issue_art[key][BuildLogConstants.KEY_LINES].values())))
            if len(new_list[-1]) > DependencyAnalyzerConstants.INT_CSV_CELL_MAX_LIMIT:  # excel cell value limit
                new_list[-1] = new_list[-1][0: DependencyAnalyzerConstants.INT_CSV_CELL_MAX_LIMIT]
            dep_issue_art[key][BuildLogConstants.KEY_POSSIBLE_CANDIDATES] = [i for i in dep_issue_art[key][BuildLogConstants.KEY_POSSIBLE_CANDIDATES] if i]
            if not dep_issue_art[key][BuildLogConstants.KEY_POSSIBLE_CANDIDATES] and not dep_issue_art[key][BuildLogConstants.KEY_LINES]:
                continue
            new_list.append(json.dumps([ob.__dict__ for ob in dep_issue_art[key][BuildLogConstants.KEY_POSSIBLE_CANDIDATES]]))
            new_list.append(str(list(set(dep_issue_art[key][BuildLogConstants.KEY_FILE_NAME]))))
            dep_issue_art_list.append(new_list)
        return dep_issue_art_list

    @staticmethod
    def check_if_traceback(line, traceback_starts, idx):
        is_traceback = re.search(BuildLogConstants.LOG_STR_TRACEBACK, line, re.M)
        start_traceback = False
        if is_traceback:
            traceback_starts[idx] = line.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE,
                                                    DependencyAnalyzerConstants.CHAR_EMPTY)
            start_traceback = True
        elif re.search(BuildLogConstants.LOG_STR_EXCEPTION, line, re.M):
            traceback_starts[idx] = line.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE,
                                                    DependencyAnalyzerConstants.CHAR_EMPTY)
        return traceback_starts, start_traceback

    @staticmethod
    def add_matches(new_match_type, line, lines_flagged, idx, match_type_list, no_module_found_pkgs):
        is_module_not_found = False
        if new_match_type:
            if new_match_type in [ErrorType.MODULE_NOT_FOUND_ERROR, ErrorType.NO_MODULE_FOUND_ERROR]:
                is_module_not_found = True
                no_module_found_pkgs[idx] = {BuildLogConstants.KEY_LINE:
                                        line.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE,
                                                    DependencyAnalyzerConstants.CHAR_EMPTY),
                                        BuildLogConstants.KEY_TYPE: new_match_type,
                                        'is_module_error': True}
            else:
                lines_flagged[idx] = {BuildLogConstants.KEY_LINE:
                                        line.replace(DependencyAnalyzerConstants.CHAR_NEW_LINE,
                                                    DependencyAnalyzerConstants.CHAR_EMPTY),
                                        BuildLogConstants.KEY_TYPE: new_match_type,
                                        'is_module_error': False}
            match_type_list.append(new_match_type)
        return lines_flagged, match_type_list, is_module_not_found, no_module_found_pkgs

    @staticmethod
    def merge_same_installed_packages(installed_packages):
        unique_pkg_dict = {}
        for pkg in installed_packages:
            if pkg.name.strip().lower() not in unique_pkg_dict:
                unique_pkg_dict[pkg.name.strip().lower()] = pkg
            else:
                if not unique_pkg_dict[pkg.name.strip().lower()].version_pinned and pkg.version_pinned:
                    unique_pkg_dict[pkg.name.strip().lower()].version_pinned = pkg.version_pinned
                elif not unique_pkg_dict[pkg.name.strip().lower()].version_constraints and pkg.version_constraints:
                    unique_pkg_dict[pkg.name.strip().lower()].version_constraints = pkg.version_constraints
                elif unique_pkg_dict[pkg.name.strip().lower()].version_constraints and pkg.version_constraints:
                    new_constraints_list = pkg.version_constraints.split(DependencyAnalyzerConstants.CHAR_SEMI_COLON)[0]\
                        .strip().split(DependencyAnalyzerConstants.CHAR_COMMA)
                    for constr in new_constraints_list:
                        if constr not in unique_pkg_dict[pkg.name.strip().lower()].version_constraints:
                            unique_pkg_dict[pkg.name.strip().lower()].version_constraints += DependencyAnalyzerConstants.CHAR_COMMA + constr
        return list(unique_pkg_dict.values())

    @staticmethod
    def localize_errors(art_details, content, priority=False):
        for line_num in art_details[BuildLogConstants.KEY_LINES]:
            pkg, file_nm = ErrorAnalyzerUtils.extract_pkg_file_nm(art_details, line_num, content)
            if pkg:
                if pkg == 'dateutil':
                    pkg = 'python-dateutil'
                ErrorAnalyzerUtils.add_if_not_added(art_details, pkg, priority)
            if file_nm:
                art_details[BuildLogConstants.KEY_FILE_NAME]\
                    .append(file_nm.split(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)[0].strip())
                    
    @staticmethod
    def extract_pkg_file_nm(art_details, line_num, content):
        pkg = None
        file_nm = None
        if art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] in\
                [ErrorType.SETUP_EGG_INFO_FAILED, ErrorType.PYTHON3_SETUP_EGG_INFO_FAILED]:
            pkg = ErrorAnalyzerUtils.extract_pkg_nm_egg_info_failure(art_details
                                                [BuildLogConstants.KEY_LINES]
                                                [line_num]
                                                [BuildLogConstants.KEY_LINE])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE]\
                in [ErrorType.PIP_INSTALL_FAILED_AND_EXITED,
                    ErrorType.PIP3_INSTALL_FAILED_AND_EXITED,
                    ErrorType.PIP_INSTALL_FAILED_TIMES,
                    ErrorType.PIP3_INSTALL_FAILED_TIMES]:
            pkg, file_nm = ErrorAnalyzerUtils.extract_pkg_nm_pip_install_failure(art_details[BuildLogConstants.KEY_LINES]
                                                            [line_num][BuildLogConstants.KEY_LINE])
            if file_nm:
                art_details[BuildLogConstants.KEY_FILE_NAME]\
                    .append(file_nm.split(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)[0].strip())
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE]\
                == ErrorType.PACKAGE_REQUIRES_PYTHON:
            pkg = ErrorAnalyzerUtils.extract_pkg_requires_python_failure(art_details[BuildLogConstants.KEY_LINES]
                                                    [line_num][BuildLogConstants.KEY_LINE])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE]\
                == ErrorType.IMPORT_ERROR:
            pkg = ErrorAnalyzerUtils.extract_pkg_import_error(art_details[BuildLogConstants.KEY_LINES][line_num]
                                        [BuildLogConstants.KEY_LINE], content[line_num - 1])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] == ErrorType.TYPE_ERROR:
            possible_traceback_lines = content[0 if line_num < 100 else line_num - 100:line_num - 1]
            pkg = ErrorAnalyzerUtils.extract_pkg_type_error(art_details[BuildLogConstants.KEY_LINES]
                                        [line_num][BuildLogConstants.KEY_LINE],
                                        possible_traceback_lines)
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE]\
                == ErrorType.PACKAGE_REQUIRES_DIFFERENT_PYTHON:
            pkg = ErrorAnalyzerUtils.extract_pkg_requires_different_python(art_details[BuildLogConstants.KEY_LINES]
                                                        [line_num][BuildLogConstants.KEY_LINE])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE]\
                in [ErrorType.PYTHON_SETUP_FAILED_EXITED, ErrorType.PYTHON3_SETUP_FAILED_EXITED]:
            file_nm = ErrorAnalyzerUtils.extract_file_name_setup_failure(art_details[BuildLogConstants.KEY_LINES]
                                                    [line_num][BuildLogConstants.KEY_LINE])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] == ErrorType.FLAKE_ERROR:
            pkg = 'flake8'
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] == ErrorType.MODULE_NOT_FOUND_ERROR:
            pkg = ErrorAnalyzerUtils.extract_pkg_module_error(art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_LINE])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] == ErrorType.NO_MODULE_FOUND_ERROR:
            pkg = ErrorAnalyzerUtils.extract_pkg_no_module_error(art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_LINE])
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] == ErrorType.CYTHON_ERROR:
            pkg = 'cython'
        elif art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_TYPE] == ErrorType.COMMAND_NOT_FOUND_ERROR:
            pkg = ErrorAnalyzerUtils.extract_command_not_found_failure(art_details[BuildLogConstants.KEY_LINES][line_num][BuildLogConstants.KEY_LINE])
        return pkg, file_nm

    @staticmethod
    def extract_command_not_found_failure(log_line):
        return log_line.split(': command not found')[0].split()[-1].strip()

    @staticmethod
    def extract_pkg_nm_egg_info_failure(log_line):
        # e.g. Command "python setup.py egg_info" failed with error code 1 in
        #       /tmp/pip-build-JkFP7S/stevedoreThe command "pip install ."
        #       failed and exited with 1 during .
        if BuildLogConstants.LOG_STR_PYTHON3 in log_line:
            line = log_line.replace(BuildLogConstants.LOG_STR_PYTHON3_EGG_INFO_FAIL,
                                    DependencyAnalyzerConstants.CHAR_EMPTY)
        else:
            line = log_line.replace(BuildLogConstants.LOG_STR_EGG_INFO_FAIL,
                                    DependencyAnalyzerConstants.CHAR_EMPTY)
        return line.strip(DependencyAnalyzerConstants.CHAR_SLASH).split(DependencyAnalyzerConstants.CHAR_SLASH)[-1].split()[0]

    @staticmethod
    def extract_pkg_nm_pip_install_failure(log_line):
        pkg = None
        file_nm = None
        if BuildLogConstants.LOG_STR_PIP3 in log_line:
            line = log_line.replace(BuildLogConstants.LOG_STR_COMMAND_PIP3_INSTALL,
                                    DependencyAnalyzerConstants.CHAR_EMPTY).strip()
        else:
            line = log_line.replace(BuildLogConstants.LOG_STR_COMMAND_PIP_INSTALL,
                                    DependencyAnalyzerConstants.CHAR_EMPTY).strip()
        if not (line.startswith(DependencyAnalyzerConstants.CHAR_HYPHEN)
                or line.startswith(DependencyAnalyzerConstants.CHAR_STOP)):
            # e.g. The command "pip install tox PyYAML Jinja2 sphinx" failed and exited with 2 during .
            pkg = line.split(BuildLogConstants.STR_FAILED)[0]\
                        .replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                DependencyAnalyzerConstants.CHAR_EMPTY)
        elif line.startswith(BuildLogConstants.LOG_STR_PIP_OPTION_R):
            # e.g. The command "pip install -r requirements.txt" failed and exited with 1 during .
            file_nm = line.split()[1].replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                            DependencyAnalyzerConstants.CHAR_EMPTY)
        elif line.startswith(BuildLogConstants.LOG_STR_PIP_OPTION_UPGRADE):
            # e.g. The command "pip install --upgrade pip==8.0.2 setuptools==20.1.1" failed and exited with 1 during .
            pkg = line.replace(BuildLogConstants.LOG_STR_PIP_OPTION_UPGRADE,
                            DependencyAnalyzerConstants.CHAR_EMPTY)\
                                .strip().split(BuildLogConstants.STR_FAILED)[0]\
                                .replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                            DependencyAnalyzerConstants.CHAR_EMPTY)
        return pkg, file_nm

    @staticmethod
    def extract_pkg_requires_python_failure(log_line):
        # e.g. This lxml version requires Python 2.7, 3.5 or later.This lxml version requires Python 2.7, 3.5 or later
        pkg = log_line.split(BuildLogConstants.LOG_STR_REQUIRES)[0].strip()
        if pkg.endswith(BuildLogConstants.LOG_STR_VERSION):
            pkg = pkg.split()[-2].strip()
        else:
            pkg = pkg.split()[-1].strip()
        return pkg

    @staticmethod
    def extract_pkg_import_error(log_line, prev_line):
        pkg = None
        if BuildLogConstants.LOG_STR_IMPORT_ERROR_CANNOT_IMPORT_NAME in log_line:
            # e.g. ImportError: cannot import name 'DefaultDict'
            pkg = log_line.split(BuildLogConstants.LOG_STR_IMPORT_ERROR_CANNOT_IMPORT_NAME)[1]\
                            .strip()\
                            .replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                    DependencyAnalyzerConstants.CHAR_EMPTY)
            if re.search(BuildLogConstants.LOG_REGEX_FROM_IMPORT, prev_line, re.M):
                # e.g. from math import ceil
                pkg = prev_line.split(BuildLogConstants.LOG_STR_IMPORT)[0].split()[-1].strip()
        elif BuildLogConstants.LOG_STR_IMPORT_ERROR_NO_MODULE in log_line:
            # e.g. ImportError: No module named 'markupsafe'
            pkg = log_line.split(BuildLogConstants.LOG_STR_IMPORT_ERROR_NO_MODULE)[1]\
                            .strip().split()[0].strip()\
                            .replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                    DependencyAnalyzerConstants.CHAR_EMPTY)\
                            .replace(DependencyAnalyzerConstants.CHAR_SINGLE_QUOTE, 
                                     DependencyAnalyzerConstants.CHAR_EMPTY)
        return pkg

    @staticmethod
    def extract_pkg_type_error(log_line, possible_traceback_lines):
        """ Searching Traceback for TypeError to see if the path to any site-package is included """
        found_traceback = False
        pkg = None
        for line in possible_traceback_lines:
            if BuildLogConstants.LOG_STR_TRACEBACK in line:
                found_traceback = True
                continue
            if found_traceback and re.search(BuildLogConstants.LOG_REGEX_SITE_PACKAGES, line, re.M):
                pkg = line.split(BuildLogConstants.LOG_STR_SITE_PACKAGES)[1]\
                    .split(DependencyAnalyzerConstants.CHAR_SLASH)[0]
                break
        return pkg

    @staticmethod
    def extract_pkg_requires_different_python(log_line):
        # e.g. ERROR: Package 'setuptools' requires a different Python: 2.7.10 not in '>=3.5'
        log_line_split = log_line.split(BuildLogConstants.LOG_STR_REQUIRES_DIFFERENT_PYTHON)
        return log_line_split[0].split()[-1]

    @staticmethod
    def extract_file_name_setup_failure(log_line):
        # e.g. The command "python setup.py install" failed and exited with 1 during 
        # e.g. The command "python3 setup.py install" failed and exited with 1 during
        if BuildLogConstants.LOG_STR_PYTHON3 in log_line:
            log_line_split = log_line.split(BuildLogConstants.LOG_STR_PYTHON3_COMMAND)[1].split()
        else:
            log_line_split = log_line.split(BuildLogConstants.LOG_STR_PYTHON_COMMAND)[1].split()
        for section in log_line_split:
            if DependencyAnalyzerConstants.PYTHON_FILE_EXT in section:
                return section

    @staticmethod
    def extract_pkg_module_error(log_line):
        if BuildLogConstants.LOG_STR_MODULE_ERROR in log_line:
            return log_line.split(
                                  BuildLogConstants.LOG_STR_MODULE_ERROR)[-1].strip()\
                                      .replace(DependencyAnalyzerConstants.CHAR_SINGLE_QUOTE,
                                               DependencyAnalyzerConstants.CHAR_EMPTY)\
                                                   .replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                                            DependencyAnalyzerConstants.CHAR_EMPTY)

    @staticmethod
    def extract_pkg_no_module_error(log_line):
        if BuildLogConstants.LOG_STR_NO_MODULE_ERROR in log_line:
            return log_line.split(
                                  BuildLogConstants.LOG_STR_NO_MODULE_ERROR)[-1].strip().split()[0]\
                                      .replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                               DependencyAnalyzerConstants.CHAR_EMPTY).replace(DependencyAnalyzerConstants.CHAR_SINGLE_QUOTE,
                                                                                               DependencyAnalyzerConstants.CHAR_EMPTY)

    @staticmethod
    def add_if_not_added(art_details, pkg, add_at_start=False):
        found = False
        installed = False
        pkg_list = pkg.replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE, DependencyAnalyzerConstants.CHAR_EMPTY).split()
        for pk in pkg_list:
            p = pk
            if not any(spec in pk for spec in DependencyAnalyzerConstants.SPECIFIERS):
                p = pk.split(DependencyAnalyzerConstants.CHAR_STOP)[0]
            pkg_info, file_nm = ErrorAnalyzerUtils.get_package_info(p)
            if not pkg_info:
                continue
            if file_nm:
                art_details[BuildLogConstants.KEY_FILE_NAME]\
                    .append(file_nm.split(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)[0].strip())
            found = False
            for last in art_details[BuildLogConstants.KEY_POSSIBLE_CANDIDATES]:
                if last.name.lower() == pkg_info.name.lower():
                    if pkg_info.version_pinned and not last.version_pinned:
                        last.version_pinned = pkg_info.version_pinned
                    if pkg_info.version_constraints and not last.version_constraints:
                        last.version_constraints = pkg_info.version_constraints
                    elif pkg_info.version_constraints and last.version_constraints:
                        new_constr_list = pkg_info.version_constraints.split(DependencyAnalyzerConstants.CHAR_SEMI_COLON)[0]\
                            .strip().strip(DependencyAnalyzerConstants.CHAR_COMMA)
                        for new_constr in new_constr_list:
                            if new_constr not in last.version_constraints:
                                last.version_constraints += DependencyAnalyzerConstants.CHAR_COMMA + new_constr
                    found = True
                    break
            if not found:
                installed = False
                for installed_pkg in art_details[BuildLogConstants.KEY_INSTALLED_PKGS]:
                    if installed_pkg.name.lower() == pkg_info.name.lower():
                        installed = True
                        if add_at_start:
                            art_details[BuildLogConstants.KEY_POSSIBLE_CANDIDATES].insert(0, installed_pkg)
                        else:
                            art_details[BuildLogConstants.KEY_POSSIBLE_CANDIDATES].append(installed_pkg)
                        break
                if not installed:
                    if add_at_start:
                        art_details[BuildLogConstants.KEY_POSSIBLE_CANDIDATES].insert(0, pkg_info)
                    else:
                        art_details[BuildLogConstants.KEY_POSSIBLE_CANDIDATES].append(pkg_info)
                    art_details[BuildLogConstants.KEY_POSSIBLE_CANDIDATES].append(pkg_info)
                    
    @staticmethod
    def get_package_info(line, next_line=None):
        """ Extracting info about package being collected/searched for and downloaded """
        file_nm = None
        package_info = ErrorAnalyzerUtils.get_pkg_name(line)  # getting package name
        if not package_info:
            return None, None
        # getting pinned/constrained versions
        pkg_nm, version_pinned, version_constraints = ErrorAnalyzerUtils.get_version_constraints(package_info.name)
        if version_pinned:
            package_info.name = pkg_nm
            package_info.is_pinned = True
            package_info.version_pinned = version_pinned
        elif version_constraints:
            package_info.name = pkg_nm
            package_info.is_constrained = True
            package_info.version_constraints = version_constraints
        if package_info.name:
            package_info.name = re.sub(BuildLogConstants.LOG_REGEX_NON_LETTER_START,
                                       DependencyAnalyzerConstants.CHAR_EMPTY, package_info.name)
            package_info.name = re.sub(BuildLogConstants.LOG_REGEX_NON_ALPHANUMERIC_END,
                                       DependencyAnalyzerConstants.CHAR_EMPTY, package_info.name)

        # checking if this is a transitive dependency
        if BuildLogConstants.LOG_STR_FROM in line:
            # extracting transitive dependencies
            transitive_deps, file_nm = ErrorAnalyzerUtils.get_transitive_dependencies(line)
            if transitive_deps:
                package_info.is_transitive = True
                package_info.transitive_deps = transitive_deps

        # getting the version actually fetched
        if next_line == line:  # only for Requirement already satisfied
            package_info.version_fetched = line.split()[-1].strip(DependencyAnalyzerConstants.CHAR_CLOSE_PARENTHESIS)\
                .strip(DependencyAnalyzerConstants.CHAR_OPEN_PARENTHESIS)
        if next_line and next_line.startswith(BuildLogConstants.LOG_STR_DOWNLOADING):
            # getting version fetched
            ver_str = ErrorAnalyzerUtils.get_downloaded_version(next_line, package_info.name)
            if ver_str:
                package_info.version_fetched = ver_str
        elif next_line and next_line.startswith(BuildLogConstants.LOG_STR_BEST_MATCH):
            # for tox installations
            # e.g. Best match: numpy 1.14.2
            ver_str = ErrorAnalyzerUtils.get_best_match_version(next_line)
            if ver_str:
                package_info.version_fetched = ver_str

        return package_info, file_nm

    @staticmethod
    def get_pkg_name(line):
        """ Extracting package name, initializing PackageInfo """
        line_split = line.split()
        if len(line_split) == 0:
            return None
        if line_split[0] == BuildLogConstants.LOG_STR_COLLECTING:
            # Line Structure: Collecting <package-name>
            if line_split[1].startswith(BuildLogConstants.LOG_GIT_LINK_START):
                return None
            package_info = PackageInfo(line_split[1])
        elif line_split[0] == BuildLogConstants.LOG_STR_SEARCHING:
            # Line Structure: Searching for <package-name>
            # for tox installations
            if line_split[2].startswith(BuildLogConstants.LOG_GIT_LINK_START):
                return None
            package_info = PackageInfo(line_split[2])
        elif line_split[0] == BuildLogConstants.LOG_STR_REQUIREMENT:
            if line_split[3].startswith(BuildLogConstants.LOG_GIT_LINK_START):
                return None
            package_info = PackageInfo(line_split[3])
        else:
            if line.startswith(BuildLogConstants.LOG_GIT_LINK_START):
                return None
            package_info = PackageInfo(line)
        return package_info

    @staticmethod
    def get_version_constraints(pkg_nm):
        """ Extracting pinned/constraints on package versions """
        version_pinned = None
        version_constraints = None
        if DependencyAnalyzerConstants.STR_EQUALS in pkg_nm:
            # e.g. lxml==4.6.1
            version_pinned = pkg_nm.split(DependencyAnalyzerConstants.STR_EQUALS)[1]
            pkg_nm = pkg_nm.split(DependencyAnalyzerConstants.STR_EQUALS)[0]
        else:
            first_spec_posn = -1
            for spec in DependencyAnalyzerConstants.SPECIFIERS:
                spec_posn = pkg_nm.find(spec)
                if spec_posn != -1:
                    if first_spec_posn == -1 or first_spec_posn > spec_posn:
                        first_spec_posn = spec_posn
            if first_spec_posn != -1:
                # e.g. lxml>=2.2.3,!=3.0.0
                version_constraints = pkg_nm[first_spec_posn:]
                pkg_nm = pkg_nm[0: first_spec_posn]
        return pkg_nm, version_pinned, version_constraints

    @staticmethod
    def get_transitive_dependencies(line):
        """ Extract which packages depend on this package """
        # e.g. Collecting pyrsistent>=0.14.0 (from jsonschema!=2.5.0,>=2.4->nbformat->notebook->jupyter->Abjad==3.0)
        # e.g. Collecting lxml (from -r requirements.txt)
        file_nm = None
        transitive_deps = None
        split_transitive = line.split(BuildLogConstants.LOG_STR_FROM)
        if not split_transitive[1].strip().startswith(DependencyAnalyzerConstants.CHAR_HYPHEN):
            # is transitive dependency
            transitive_deps = split_transitive[1]\
                .replace(DependencyAnalyzerConstants.CHAR_CLOSE_PARENTHESIS,
                            DependencyAnalyzerConstants.CHAR_EMPTY)
            if BuildLogConstants.LOG_STR_TRANSITIVE_DEP_REQ_FILE_SEPERATOR in transitive_deps:
                file_nm = transitive_deps.split(BuildLogConstants.LOG_STR_TRANSITIVE_DEP_REQ_FILE_SEPERATOR)[-1]\
                    .strip()
        elif split_transitive[1].strip().startswith(BuildLogConstants.LOG_STR_PIP_OPTION_R):
            file_nm = split_transitive[1].split(BuildLogConstants.LOG_STR_REQUIREMENTS_FLAG)[-1].strip()
        return transitive_deps, file_nm

    @staticmethod
    def get_downloaded_version(line, pkg_nm):
        """ Get downloaded version """
        # e.g. Collecting docopt>=0.6.1 (from coveralls==1.2.0)
        # Downloading https://files.pythonhosted.org/packages/a2/55/8f8cab2afd404cf578136ef2cc5dfb50baa1761b68c9da1fb1e4eed343c9/docopt-0.6.2.tar.gz
        line_split = line.split(DependencyAnalyzerConstants.CHAR_SLASH)
        ver_str = None
        for section in line_split:
            if section.startswith(pkg_nm):
                ver_str = section.replace(pkg_nm +
                                            DependencyAnalyzerConstants.CHAR_HYPHEN,
                                        DependencyAnalyzerConstants.CHAR_EMPTY)
                ver_str = ver_str.split(DependencyAnalyzerConstants.CHAR_HYPHEN)[0]\
                    .strip(DependencyAnalyzerConstants.CHAR_HYPHEN)
                ver_str = ver_str.replace(BuildLogConstants.PACKAGE_TAR_SUFFIX,
                                            DependencyAnalyzerConstants.CHAR_EMPTY)
                ver_str = ver_str.split(DependencyAnalyzerConstants.CHAR_HYPHEN)[0]
        return ver_str

    @staticmethod
    def get_best_match_version(line):
        """ For tox initializations, line displaying best matched version """
        return line.replace(BuildLogConstants.LOG_STR_BEST_MATCH,
                            DependencyAnalyzerConstants.CHAR_EMPTY).split()[-1].strip()

    @staticmethod
    def extract_packages_from_tracebacks(traceback_starts, art_details, content, orig_content, repo_name):
        for idx in traceback_starts:
            if idx + 1 < len(content):
                file_line = content[idx + 1]
                # check if traceback shows file location
                if not file_line.startswith(BuildLogConstants.LOG_STR_FILE):
                    continue
                # check if same error trace exists in the original log
                found_in_original = False
                try:
                    search_str_in_orig = file_line.split(DependencyAnalyzerConstants.CHAR_SLASH)[-2]\
                                            + DependencyAnalyzerConstants.CHAR_SLASH +\
                                                file_line.split(DependencyAnalyzerConstants.CHAR_SLASH)[-1]
                except IndexError:
                    search_str_in_orig = file_line
                if orig_content:
                    for orig_idx in range(0, len(orig_content) - 1):
                        if orig_content[orig_idx] == content[idx] and search_str_in_orig in orig_content[orig_idx + 1]:
                            found_in_original = True
                            break
                if found_in_original:
                    continue
                file_line_idx = idx + 1
                pkg_names = []
                while file_line_idx < len(content):
                    if not content[file_line_idx].startswith(BuildLogConstants.LOG_STR_FILE):
                        file_line_idx +=1
                        continue
                    if content[file_line_idx].find(BuildLogConstants.LOG_STR_SITE_PACKAGES) == -1:
                        file_line_idx += 1
                        continue
                    split_line = content[file_line_idx].split(BuildLogConstants.LOG_STR_SITE_PACKAGES)[-1]
                    pkg_name = split_line.split(DependencyAnalyzerConstants.CHAR_SLASH)[0].strip()
                    if DependencyAnalyzerConstants.PYTHON_FILE_EXT + DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE in pkg_name:
                        pkg_name = pkg_name.split(DependencyAnalyzerConstants.PYTHON_FILE_EXT + DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE)[0]
                    file_line_idx += 1
                    if pkg_name in repo_name.split(DependencyAnalyzerConstants.CHAR_SLASH):
                        continue
                    if pkg_name in pkg_names:
                        continue
                    pkg_names.append(pkg_name)
                for p in pkg_names:
                    if art_details['is_module_error']:
                        ErrorAnalyzerUtils.add_if_not_added(art_details, p, False)
                    else:
                        ErrorAnalyzerUtils.add_if_not_added(art_details, p, True)
