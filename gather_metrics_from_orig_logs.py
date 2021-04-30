import sys
import os
import re
import json
from time import sleep
from os.path import isfile, join
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from build_log_const import BuildLogConstants
from package_info import PackageInfo
from bugswarm.common.log_downloader import download_log


def main(args):
    path = args[2]
    orig_log_path = args[4]
    op = []
    artifact_dict = DependencyAnalyzerUtils.get_artifact_dict(path)
    iter_count = 0
    proj_dep_buckets = {'1-5': 0, '6-10': 0, '11-15': 0, '16-25': 0,
                        '26-100': 0, '>100':0}
    tran_dep_buckets = {'1-5': 0, '6-10': 0, '11-15': 0, '16-20': 0,
                        '21-25': 0, '26-50': 0, '51-75': 0, '76-100': 0,
                        '>100': 0}
    total_pinned = {'project': 0, 'transitive': 0, 'total': 0}
    total_constrained = {'project': 0, 'transitive': 0, 'total': 0}
    total_unconstrained = {'project': 0, 'transitive': 0, 'total': 0}
    for img_tag in artifact_dict:
        if artifact_dict[img_tag][DependencyAnalyzerConstants.LANGUAGE_KEY]\
                != DependencyAnalyzerConstants.LANGUAGE_PYTHON:
            continue
        if ('terasoluna' in img_tag and img_tag not in ['terasolunaorg-guideline-166664541', 'terasolunaorg-guideline-167349415', 'terasolunaorg-guideline-166664553']) or 'openfisca' in img_tag:
            continue
        print(iter_count)
        iter_count += 1
        # failed_orig_log_path = download_orig_log(artifact_dict[img_tag], img_tag, 'failed')
        failed_orig_log_path = join(orig_log_path, DependencyAnalyzerConstants.ORIG_LOG_FILENM_PATTERN.format(img_tag, 'failed'))
        if not isfile(failed_orig_log_path):
            continue
        installed_pkgs = check_log(failed_orig_log_path)
        count, pinned, constrained, unconstrained, transitive = gather_metrics(installed_pkgs)
        if count > 0:
            op.append([img_tag, 'failed', count, pinned, constrained, unconstrained,
                      transitive['count'], transitive['pinned'], transitive['constrained'],
                      transitive['unconstrained'], json.dumps([ob.__dict__ for ob in installed_pkgs])])
            tran_dep_buckets, proj_dep_buckets, total_pinned, total_constrained, total_unconstrained = update_dep_counts(
                tran_dep_buckets, proj_dep_buckets, total_pinned, total_constrained, total_unconstrained,
                count, pinned, constrained, unconstrained, transitive
            )
        # passed_orig_log_path = download_orig_log(artifact_dict[img_tag], img_tag, 'passed')
        passed_orig_log_path = join(orig_log_path, DependencyAnalyzerConstants.ORIG_LOG_FILENM_PATTERN.format(img_tag, 'passed'))
        if not isfile(passed_orig_log_path):
            continue
        installed_pkgs = check_log(passed_orig_log_path)
        count, pinned, constrained, unconstrained, transitive = gather_metrics(installed_pkgs)
        if count > 0:
            op.append([img_tag, 'passed', count, pinned, constrained, unconstrained,
                      transitive['count'], transitive['pinned'], transitive['constrained'],
                      transitive['unconstrained'], json.dumps([ob.__dict__ for ob in installed_pkgs])])
            tran_dep_buckets, proj_dep_buckets, total_pinned, total_constrained, total_unconstrained = update_dep_counts(
                tran_dep_buckets, proj_dep_buckets, total_pinned, total_constrained, total_unconstrained,
                count, pinned, constrained, unconstrained, transitive
            )
    DependencyAnalyzerUtils.write_to_csv(op,
                                         ['Artifact Image Tag', 'Pass/Fail', 'Project Dependency Count',
                                          'Pinned Dependency Count', 'Constrained Dependency Count',
                                          'Unconstrained Dependency Count', 'Transitive Dependency Count',
                                          'Transitive Pinned Dependency Count', 'Transitive Constrained Dependency Count',
                                          'Transitive Unconstrained Dependency Count', 'Installed Packages'],
                                         'orig_log_metrics.csv')
    print('==========**** BugSwarm METRICS FINAL OUTPUT ****==========')
    print('Figure 2a: Builds by number of project dependencies')
    for key in proj_dep_buckets:
        print('{} dependencies: {} builds'.format(key, proj_dep_buckets[key]))
    print('===========================================')
    print('Fig 2b: Builds by number of transitive dependencies')
    for key in tran_dep_buckets:
        print('{} dependencies: {} builds'.format(key, tran_dep_buckets[key]))
    print('===========================================')
    print('Fig 3: Dependencies by Version Specification')
    print('Pinned Version Specification')
    print('Project Dependencies: {}'.format(total_pinned['project']))
    print('Transitive Dependencies: {}'.format(total_pinned['transitive']))
    print('Total Dependencies: {}'.format(total_pinned['total']))
    print('====================')
    print('Constrained Version Specification')
    print('Project Dependencies: {}'.format(total_constrained['project']))
    print('Transitive Dependencies: {}'.format(total_constrained['transitive']))
    print('Total Dependencies: {}'.format(total_constrained['total']))
    print('====================')
    print('Unconstrained Version Specification')
    print('Project Dependencies: {}'.format(total_unconstrained['project']))
    print('Transitive Dependencies: {}'.format(total_unconstrained['transitive']))
    print('Total Dependencies: {}'.format(total_unconstrained['total']))
    print('==========**** END OF OUTPUT ****==========')

def update_dep_counts(
            tran_dep_buckets, proj_dep_buckets, total_pinned, total_constrained, total_unconstrained,
            count, pinned, constrained, unconstrained, transitive
        ):
    if count >= 1 and count <= 5:
        proj_dep_buckets['1-5'] = proj_dep_buckets['1-5'] + 1
    elif count >= 6 and count <= 10:
        proj_dep_buckets['6-10'] = proj_dep_buckets['6-10'] + 1
    elif count >= 11 and count <= 15:
        proj_dep_buckets['11-15'] = proj_dep_buckets['11-15'] + 1
    elif count >= 16 and count <= 25:
        proj_dep_buckets['16-25'] = proj_dep_buckets['16-25'] + 1
    elif count >= 26 and count <= 100:
        proj_dep_buckets['26-100'] = proj_dep_buckets['26-100'] + 1
    elif count > 100:
        proj_dep_buckets['>100'] = proj_dep_buckets['>100'] + 1

    if transitive['count'] >= 1 and transitive['count'] <= 5:
        tran_dep_buckets['1-5'] = tran_dep_buckets['1-5'] + 1
    elif transitive['count'] >= 6 and transitive['count'] <= 10:
        tran_dep_buckets['6-10'] = tran_dep_buckets['6-10'] + 1
    elif transitive['count'] >= 11 and transitive['count'] <= 15:
        tran_dep_buckets['11-15'] = tran_dep_buckets['11-15'] + 1
    elif transitive['count'] >= 16 and transitive['count'] <= 20:
        tran_dep_buckets['16-20'] = tran_dep_buckets['16-20'] + 1
    elif transitive['count'] >= 21 and transitive['count'] <= 25:
        tran_dep_buckets['21-25'] = tran_dep_buckets['21-25'] + 1
    elif transitive['count'] >= 26 and transitive['count'] <= 50:
        tran_dep_buckets['26-50'] = tran_dep_buckets['26-50'] + 1
    elif transitive['count'] >= 51 and transitive['count'] <= 75:
        tran_dep_buckets['51-75'] = tran_dep_buckets['51-75'] + 1
    elif transitive['count'] >= 76 and transitive['count'] <= 100:
        tran_dep_buckets['76-100'] = tran_dep_buckets['76-100'] + 1
    elif transitive['count'] > 100:
        tran_dep_buckets['>100'] = tran_dep_buckets['>100'] + 1

    total_pinned['project'] = total_pinned['project'] + pinned
    total_pinned['transitive'] = total_pinned['transitive'] + transitive['pinned']
    total_pinned['total'] = total_pinned['total'] + pinned + transitive['pinned']

    total_constrained['project'] = total_constrained['project'] + constrained
    total_constrained['transitive'] = total_constrained['transitive'] + transitive['constrained']
    total_constrained['total'] = total_constrained['total'] + constrained + transitive['constrained']

    total_unconstrained['project'] = total_unconstrained['project'] + unconstrained
    total_unconstrained['transitive'] = total_unconstrained['transitive'] + transitive['unconstrained']
    total_unconstrained['total'] = total_unconstrained['total'] + unconstrained + transitive['unconstrained']

    return tran_dep_buckets, proj_dep_buckets, total_pinned, total_constrained, total_unconstrained




def gather_metrics(installed_pkgs):
    count = 0
    pinned = 0
    constrained = 0
    unconstrained = 0
    transitive = {'count': 0, 'pinned': 0, 'constrained': 0, 'unconstrained': 0}
    for pkg in installed_pkgs:
        is_transitive = False
        if pkg.transitive_deps:
            is_transitive = True
            transitive['count'] += 1
        else:
            count += 1
        if is_transitive and pkg.version_pinned:
            transitive['pinned'] += 1
            continue
        elif pkg.version_pinned:
            pinned += 1
            continue
        if is_transitive and pkg.version_constraints:
            transitive['constrained'] += 1
            continue
        elif pkg.version_constraints:
            constrained += 1
            continue
        if is_transitive:
            transitive['unconstrained'] += 1
        else:
            unconstrained += 1
    return count, pinned, constrained, unconstrained, transitive


def check_log(log_path):
    ansi_escape = re.compile(DependencyAnalyzerConstants.ANSI_ESCAPE_STR, re.M)
    installed_packages = []
    last_identified_package = {}
    content = []
    with open(log_path, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
        content = [x.strip() for x in f.readlines()]
    for idx in range(0, len(content)):
        line = content[idx]
        line = ansi_escape.sub(DependencyAnalyzerConstants.CHAR_EMPTY, line)
        if line.startswith(BuildLogConstants.LOG_STR_COLLECTING):
            last_identified_package, file_nm = get_package_info(line, content[idx + 1])
            if not last_identified_package:
                continue
            installed_packages.append(last_identified_package)
            continue
        elif line.startswith(BuildLogConstants.LOG_STR_SEARCHING):
            last_identified_package, file_nm = get_package_info(line, content[idx + 3])
            if not last_identified_package:
                continue
            installed_packages.append(last_identified_package)
            continue
        elif line.startswith(BuildLogConstants.LOG_STR_DOWNLOADING)\
                or line.startswith(BuildLogConstants.LOG_STR_BEST_MATCH):
            continue
    return installed_packages


def get_package_info(line, next_line=None):
    """ Extracting info about package being collected/searched for and downloaded """
    file_nm = None
    package_info = get_pkg_name(line)  # getting package name
    if not package_info:
        return None, None
    # getting pinned/constrained versions
    pkg_nm, version_pinned, version_constraints = get_version_constraints(package_info.name)
    if version_pinned:
        package_info.name = pkg_nm
        package_info.is_pinned = True
        package_info.version_pinned = version_pinned
    elif version_constraints:
        package_info.name = pkg_nm
        package_info.is_constrained = True
        package_info.version_constraints = version_constraints
    if package_info.name:
        package_info.name = re.sub('^[^A-Za-z]+', '', package_info.name)
        package_info.name = re.sub('[^A-Za-z0-9]+$', '', package_info.name)
    # checking if this is a transitive dependency
    if BuildLogConstants.LOG_STR_FROM in line:
        # extracting transitive dependencies
        transitive_deps, file_nm = get_transitive_dependencies(line)
        if transitive_deps:
            package_info.is_transitive = True
            package_info.transitive_deps = transitive_deps

    # getting the version actually fetched
    if next_line and next_line.startswith(BuildLogConstants.LOG_STR_DOWNLOADING):
        # getting version fetched
        ver_str = get_downloaded_version(next_line, package_info.name)
        if ver_str:
            package_info.version_fetched = ver_str
    elif next_line and next_line.startswith(BuildLogConstants.LOG_STR_BEST_MATCH):
        # for tox installations
        # e.g. Best match: numpy 1.14.2
        ver_str = get_best_match_version(next_line)
        if ver_str:
            package_info.version_fetched = ver_str

    return package_info, file_nm


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
        file_nm = split_transitive[1].split('-r ')[-1].strip()
    return transitive_deps, file_nm


def get_pkg_name(line):
    """ Extracting package name, initializing PackageInfo """
    line_split = line.split()
    if len(line_split) == 0:
        return None
    if line_split[0] == BuildLogConstants.LOG_STR_COLLECTING:
        # Line Structure: Collecting <package-name>
        if line_split[1].startswith('git+https'):
            return None
        package_info = PackageInfo(line_split[1])
    elif line_split[0] == BuildLogConstants.LOG_STR_SEARCHING:
        # Line Structure: Searching for <package-name>
        # for tox installations
        if line_split[2].startswith('git+https'):
            return None
        package_info = PackageInfo(line_split[2])
    else:
        if line.startswith('git+https'):
            return None
        package_info = PackageInfo(line)
    return package_info


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


def get_best_match_version(line):
    """ For tox initializations, line displaying best matched version """
    return line.replace(BuildLogConstants.LOG_STR_BEST_MATCH,
                        DependencyAnalyzerConstants.CHAR_EMPTY).split()[-1].strip()


def download_orig_log(art, img_tag, f_or_p):
    job_id = art['{}_job'.format(f_or_p)]['job_id']
    original_log_name = '{}.{}.orig.log'.format(img_tag, f_or_p)
    downloaded = download_log(job_id, join(os.getcwd(), original_log_name))
    if downloaded:
        return join(os.getcwd(), original_log_name)
    return None


if __name__ == '__main__':
    # python3 gather_metrics_from_orig_logs.py 
    # -path <path to artifacts.json>
    main(sys.argv)
