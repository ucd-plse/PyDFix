import requests
from http import HTTPStatus
import re
import os
from os.path import join
from dateutil import parser
from packaging.version import parse
from dependency_analyzer_utils import DependencyAnalyzerUtils
from dependency_analyzer_const import DependencyAnalyzerConstants


class SolverUtils:
    @staticmethod
    def get_source_code_from_docker_image(artifact, f_or_p, log_output_content, dir_loc):
        container_name = '{}_{}'.format(artifact['image_tag'], f_or_p)
        docker_container_cmd = DependencyAnalyzerConstants.DOCKER_RUN_IMAGE_CMD.format(container_name, artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY])
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_container_cmd)
        if not ok:
            log_output_content.append(stderr)
            log_output_content.append('Failed to run Docker container')
            return False, log_output_content
        get_container_id_cmd = DependencyAnalyzerConstants.DOCKER_GET_CONTAINER_ID_CMD + container_name + '"'
        _, container_id, _, _ = DependencyAnalyzerUtils._run_command(get_container_id_cmd)
        if not container_id:
            log_output_content.append('Failed to run Docker container')
            return False, log_output_content
        docker_cp_src_code = 'docker cp {}:/home/travis/build/{}/{} {}'.format(container_id, f_or_p,
                                                                               artifact[DependencyAnalyzerConstants.REPO_KEY],
                                                                               dir_loc)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_cp_src_code)
        SolverUtils.remove_docker_container(container_name)
        if not ok:
            log_output_content.append(stderr)
            log_output_content.append('Failed to run Docker container')
            return False, log_output_content
        return True, log_output_content

    @staticmethod
    def remove_docker_container(container_name):
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
                                                                     DependencyAnalyzerConstants.DOCKER_REMOVE_CONTAINER.format(container_name))

    @staticmethod
    def generate_patch_combos(candidates, commit_date, repo_name, log_output_content, cloned_repo_dir, dep_files):
        """ Generate pinned patches for all possible candidates """
        patch_combos = []
        for candidate in candidates:
            pin_version = None
            name = candidate['_name']
            if name == 'attr':
                name = 'attrs'
            if SolverUtils.check_if_patch_exists(patch_combos, name):
                continue
            constraints = candidate['_version_constraints']
            pinned_dep_patch_alternates = []
            if candidate['_is_pinned'] or candidate['_version_pinned']:
                pinned_dep_patch_alternates = SolverUtils.get_pinned_dep_patch_alternates(candidate['_name'])
                if not pinned_dep_patch_alternates:
                    continue
                log_output_content.append('Found pinned candidate... ')
                if not SolverUtils.remove_pin(candidate['_name'], candidate['_version_pinned'], cloned_repo_dir, dep_files):
                    log_output_content.append('Failed to remove pin for {}...skipping'.format(candidate['_name']))
                    # continue
                # add constraint to avoid pinned version
                if constraints:
                    constraints += ',!=' + candidate['_version_pinned']
                else:
                    constraints = '!=' + candidate['_version_pinned']
            # check if transitive dependencies
            transitive_dep_patches = []
            if candidate['_is_transitive'] and candidate['_transitive_deps']:
                dependency_chain = candidate['_transitive_deps'].split('->')
                # remove file name from dependency chain
                dependency_chain = [i.strip() for i in dependency_chain if not i.strip().startswith('-r')]
                # remove repo name from dependency chain
                dependency_chain = [dep for dep in dependency_chain if not any(x in dep for x in repo_name.split('/'))]
                dependency_chain.reverse()
                for dep in dependency_chain:
                    pinned_tran_dep_alternatives = None
                    if any(spec in dep for spec in DependencyAnalyzerConstants.SPECIFIERS):
                        dep_name, dep_constraints, found_spec = SolverUtils.split_name_and_constraint(dep)
                        if SolverUtils.check_if_patch_exists(patch_combos, dep_name):
                            continue
                        if found_spec in ['==', '===']:
                            pinned_tran_dep_alternatives = SolverUtils.get_pinned_dep_patch_alternates(dep_name)
                            if not SolverUtils.remove_pin(dep_name, dep_constraints.split(found_spec)[-1], cloned_repo_dir, dep_files):
                                log_output_content.append('Failed to remove pin for transitive dependencies {}...skipping'.format(candidate['_name']))
                            pinned_tran_dep_constraint = '!=' + dep_constraints.split(found_spec)[-1]
                            dep_pin_version, log_output_content = SolverUtils.get_constrained_version(dep_name, pinned_tran_dep_constraint, commit_date, log_output_content)
                        else:
                            dep_pin_version, log_output_content = SolverUtils.get_constrained_version(dep_name, dep_constraints, commit_date, log_output_content)
                    elif re.match(r'[A-Za-z0-9]+ \([0-9\.]+\)?', dep):
                        dep_name = dep.split()[0]
                        dep_constraints = dep.split()[1].strip().strip('(').strip(')')
                        pinned_tran_dep_alternatives = SolverUtils.get_pinned_dep_patch_alternates(dep_name)
                        if not SolverUtils.remove_pin(dep_name, dep_constraints, cloned_repo_dir, dep_files):
                            log_output_content.append('Failed to remove pin for transitive dependencies {}'.format(dep_name))
                        pinned_tran_dep_constraint = '!=' + dep_constraints
                        dep_pin_version, log_output_content = SolverUtils.get_constrained_version(dep_name, pinned_tran_dep_constraint, commit_date, log_output_content)
                    else:
                        dep_name = dep
                        if SolverUtils.check_if_patch_exists(patch_combos, dep_name):
                            continue
                        dep_pin_version, log_output_content = SolverUtils.find_correct_version(dep, SolverUtils.get_version_history(dep), commit_date, log_output_content)
                    if not dep_pin_version:
                        log_output_content.append('Unable to find suitable version for transitive dependency {} with constraints {}'.format(dep_name, constraints))
                        continue
                    transitive_dep_patches.append({'name': dep_name, 'version': dep_pin_version, 'applied': False, 'included': False})
                    if pinned_tran_dep_alternatives:
                        transitive_dep_patches.extend(pinned_tran_dep_alternatives)
            # check for constraints in candidate
            if constraints:
                pin_version, log_output_content = SolverUtils.get_constrained_version(name, constraints, commit_date, log_output_content)
            else:
                pin_version, log_output_content = SolverUtils.find_correct_version(name, SolverUtils.get_version_history(name), commit_date, log_output_content)

            if not pin_version and not pinned_dep_patch_alternates:
                log_output_content.append('Unable to find suitable version for {} with constraints {}'.format(name, constraints))
                continue
            elif not pin_version and pinned_dep_patch_alternates:
                patch_combos = pinned_dep_patch_alternates
            else:
                patch_combos.append({'name': name, 'version': pin_version, 'applied': False, 'included': False})
                patch_combos.extend(pinned_dep_patch_alternates)
            if transitive_dep_patches:
                transitive_dep_patches.extend(patch_combos)
                return transitive_dep_patches, log_output_content
        return patch_combos, log_output_content

    @staticmethod
    def check_if_patch_exists(patch_combos, dep_name):
        for patch in patch_combos:
            if patch['name'] == dep_name:
                return True
        return False

    @staticmethod
    def get_pinned_dep_patch_alternates(pkg_nm):
        latest_version = SolverUtils.get_latest_version(pkg_nm)
        alternates = []
        if latest_version:
            alternates.append({'name': pkg_nm, 'version': latest_version, 'applied': False, 'included': False})
        # alternates.append({'name': '', 'version': '', 'applied': False, 'included': False})
        return alternates

    @staticmethod
    def get_latest_version(pkg_nm):
        version_history = SolverUtils.get_version_history(pkg_nm)
        if not version_history:
            return None
        for release in sorted(version_history[DependencyAnalyzerConstants.PYPI_API_RELEASES_KEY], key=parse, reverse=True):
            return release

    @staticmethod
    def get_version_history(package, version=None):
        """ Fetching all release versions of package dependency from PyPI JSON API """
        package_history_url = DependencyAnalyzerConstants.PYPI_PKG_HISTORY_URL.format(package)
        if version is not None:
            package_history_url = DependencyAnalyzerConstants.PYPI_VERSION_HISTORY_URL.format(package, version)
        history_response = requests.get(package_history_url, DependencyAnalyzerConstants.STR_ENCODING_UTF8, auth=(
        DependencyAnalyzerConstants.GITHUB_USER_NAME, DependencyAnalyzerConstants.GITHUB_AUTH_TOKEN))
        if history_response.status_code == HTTPStatus.NOT_FOUND:
            return None
        history_dict = history_response.json()
        return history_dict

    @staticmethod
    def remove_pin(candidate_name, pinned_version, cloned_repo_dir, dep_files):
        # all_files = os.listdir(cloned_repo_dir)
        requirements_txt_file_name_regex = r'(.*)requirements(.*)\.txt'
        if dep_files:
            dep_files = eval(dep_files)
        for root, subdirs, files in os.walk(cloned_repo_dir):
            dep_files_found = []
            for d in dep_files:
                for f in files:
                    if d == f:
                        dep_files_found.append(f)
            # dep_files_found = [x for x in dep_files if x in files]
            for d in dep_files_found:
                if SolverUtils.edit_dep_file(join(root, d), candidate_name, pinned_version):
                    return True
            for f in files:
                if re.match(requirements_txt_file_name_regex, f) and SolverUtils.edit_dep_file(join(root, f), candidate_name, pinned_version):
                    return True
                elif f == 'setup.py' and SolverUtils.edit_dep_file(join(root, f), candidate_name, pinned_version):
                    return True
                elif f == '.travis.yml' and SolverUtils.edit_dep_file(join(root, f), candidate_name, pinned_version):
                    return True
                else:
                    continue
        return False

    @staticmethod
    def edit_dep_file(file_path, candidate_name, pinned_version):
        search_str = candidate_name + '===?' + pinned_version.replace('.', '\.')
        replace_str = '===?' + pinned_version.replace('.', '\.')
        lines = []
        file_contents = []
        found_dep = False
        with open(file_path, 'r', encoding='utf-8') as f:
            file_contents = f.read().splitlines()
        for l in file_contents:
            if re.search(search_str, l, re.M):
                found_dep = True
                if file_path.endswith('.txt'):
                    continue
                elif file_path.endswith('.py'):
                    lines.append(re.sub(replace_str + ',?', '', l))
                elif file_path.endswith('.yml'):
                    if re.search('pip install -U (.*)' + search_str, l, re.M):
                        new_line = re.sub(replace_str, '', l)
                        new_line = re.sub('-U', '', new_line)
                    elif re.search('pip install --upgrade (.*)' + search_str, l, re.M):
                        new_line = re.sub(replace_str, '', l)
                        new_line = re.sub('--upgrade', '', new_line)
                    else:
                        new_line = re.sub(replace_str, '', l)
                    lines.append(new_line)
                else:
                    lines.append(l)
            else:
                lines.append(l)
        if found_dep:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        return found_dep

    @staticmethod
    def get_constrained_version(dep_name, constraint, commit_date, log_output_content):
        """ Pin correct version satisfying all version constraints """
        # for multiple constraints like !=1.25.0,!=1.25.1,<1.26,>=1.21.1
        constraint_list = constraint.strip().split(DependencyAnalyzerConstants.CHAR_COMMA)
        constraint_list = [c.strip(';') for c in constraint_list]
        if len(constraint_list) == 1 and DependencyAnalyzerConstants.STR_GREATER_EQUALS in constraint_list[0]:
            ver = SolverUtils.get_version_history(dep_name, constraint_list[0].split(DependencyAnalyzerConstants.STR_GREATER_EQUALS)[-1].strip())
            if dep_name == 'typing' and constraint_list[0].split(DependencyAnalyzerConstants.STR_GREATER_EQUALS)[-1].strip() == '3.5.2':
                return '3.5.2.2', log_output_content
            if ver:
                return constraint_list[0].split(DependencyAnalyzerConstants.STR_GREATER_EQUALS)[-1].strip(), log_output_content
        elif len(constraint_list) == 1 and DependencyAnalyzerConstants.STR_LESSER_EQUALS in constraint_list[0]:
            if SolverUtils.get_version_history(dep_name, constraint_list[0].split(DependencyAnalyzerConstants.STR_LESSER_EQUALS)[-1].strip()):
                return constraint_list[0].split(DependencyAnalyzerConstants.STR_LESSER_EQUALS)[-1].strip(), log_output_content

        return SolverUtils.find_correct_version(dep_name, SolverUtils.get_version_history(dep_name), commit_date, log_output_content, constraint_list)

    @staticmethod
    def find_correct_version(package, history_dict, commit_date, log_output_content, constraints=None):
        """ Find correct version for unpinned and constrained dependencies """
        if not history_dict:
            log_output_content.append('No history available for {}'.format(package))
            return None, log_output_content
        commit_time = parser.parse(commit_date).replace(tzinfo=None)
        for release in sorted(history_dict[DependencyAnalyzerConstants.PYPI_API_RELEASES_KEY], key=parse, reverse=True):
            for subrelease in range(0, len(history_dict[DependencyAnalyzerConstants.PYPI_API_RELEASES_KEY][release])):
                upload_time = history_dict[DependencyAnalyzerConstants.PYPI_API_RELEASES_KEY][release][subrelease][DependencyAnalyzerConstants.PYPI_API_UPLOAD_TIME_KEY]
                upload_time = parser.parse(upload_time).replace(tzinfo=None)
                if upload_time <= commit_time:
                    if package == 'typing' and release == '3.5.2':
                        release = '3.5.2.2'
                    if constraints:
                        constraints_satisfied = True
                        for constraint in constraints:
                            constraints_satisfied = constraints_satisfied and SolverUtils.check_constraint_satisfaction(release, constraint)
                        if constraints_satisfied:
                            return release, log_output_content
                    else:
                        return release, log_output_content
        return None, log_output_content

    @staticmethod
    def check_constraint_satisfaction(release, constraint):
        """ Check if constraints are satisfied by this release """
        if '>=' in constraint and release < constraint.split('>=')[-1]:
            return False
        elif DependencyAnalyzerConstants.CHAR_GREATER in constraint and '=' not in constraint and release <= constraint.split(DependencyAnalyzerConstants.CHAR_GREATER)[-1]:
            return False
        elif '<=' in constraint and release > constraint.split('<=')[-1]:
            return False
        elif DependencyAnalyzerConstants.CHAR_LESSER in constraint and '=' not in constraint and release >= constraint.split(DependencyAnalyzerConstants.CHAR_LESSER)[-1]:
            return False
        elif DependencyAnalyzerConstants.STR_NOT_EQUALS in constraint and release == constraint.split(DependencyAnalyzerConstants.STR_NOT_EQUALS)[-1]:
            return False
        elif DependencyAnalyzerConstants.STR_NOT_EQUALS_TILDE in constraint and release == constraint.split(DependencyAnalyzerConstants.STR_NOT_EQUALS_TILDE)[-1]:
            return False
        return True

    @staticmethod
    def split_name_and_constraint(dep_str):
        first_spec_pos = len(dep_str)
        found_spec = None
        for spec in DependencyAnalyzerConstants.SPECIFIERS:
            pos = dep_str.find(spec)
            if pos != -1 and pos < first_spec_pos:
                first_spec_pos = pos
                found_spec = spec
        return dep_str[:first_spec_pos], dep_str[first_spec_pos:], found_spec
