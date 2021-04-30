import os
from os.path import join, isdir, isfile, expanduser
import zipfile
import requests
import shutil
import traceback
from http import HTTPStatus
from pathlib import Path
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from travis_yml_generator import TravisYMLGenerator


class ReproducedLogGenerator:
    def __init__(self, dataset_idx):
        self._dataset_idx = dataset_idx

    def start_log_gen(self, artifact, f_or_p, output_path, component_path):
        try:
            if self._dataset_idx == 1:
                return self.bugswarm_log_generate(artifact, f_or_p, output_path)
            else:
                return self.bugsinpy_log_generation(artifact, output_path, component_path)
        except Exception as e:
            traceback.print_exc()
            print(e)
            print('Failed to generate reproduced logs')
            if self._dataset_idx == 1:
                self.bugswarm_cleanup(artifact, f_or_p)
            else:
                self.bugsinpy_cleanup(artifact.split('_')[0], artifact.split('_')[1], artifact.split('_')[2])
            return False

    def bugswarm_log_generate(self, artifact, f_or_p, op_path):
        img_tag = artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY]
        print('Processing...{}_{}'.format(img_tag, f_or_p))
        diff_url = artifact[DependencyAnalyzerConstants.DIFF_URL_KEY]
        response = requests.get(diff_url, auth=(
        DependencyAnalyzerConstants.GITHUB_USER_NAME, DependencyAnalyzerConstants.GITHUB_AUTH_TOKEN))
        if response.status_code != HTTPStatus.OK:
            return None
        if f_or_p == DependencyAnalyzerConstants.STR_FAILED:
            commit = diff_url.split(DependencyAnalyzerConstants.STR_TWO_DOTS)[0].split(DependencyAnalyzerConstants.CHAR_SLASH)[-1]
        else:
            commit = diff_url.split(DependencyAnalyzerConstants.STR_TWO_DOTS)[-1]
        cwd = os.getcwd()
        clone_location = join(cwd, img_tag + DependencyAnalyzerConstants.CHAR_UNDERSCORE + f_or_p)
        if not self.run_commit_build(commit, artifact[DependencyAnalyzerConstants.REPO_KEY], clone_location, op_path, f_or_p, img_tag):
            return None
        self.bugswarm_cleanup(artifact, f_or_p)

    def bugswarm_cleanup(self, artifact, f_or_p):
        cwd = os.getcwd()
        img_tag = artifact[DependencyAnalyzerConstants.IMAGE_TAG_KEY]
        clone_location = join(cwd, img_tag + DependencyAnalyzerConstants.CHAR_UNDERSCORE + f_or_p)
        if os.path.exists('resp_{}_{}.zip'.format(img_tag, f_or_p)):
            os.remove('resp_{}_{}.zip'.format(img_tag, f_or_p))
        if os.path.isdir(clone_location):
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo rm -rf {}'.format(clone_location))
        _, container_id, _, _ = DependencyAnalyzerUtils._run_command('docker rm -f /{}_{}'.format(img_tag, f_or_p))

    def run_commit_build(self, commit, repo_name, clone_location, op_path, f_or_p, img_tag):
        zip_download_url = 'https://api.github.com/repos/{}/zipball/{}'.format(repo_name, commit)
        response = requests.get(zip_download_url, stream=True, auth=(
            DependencyAnalyzerConstants.GITHUB_USER_NAME, DependencyAnalyzerConstants.GITHUB_AUTH_TOKEN))
        if response.status_code != HTTPStatus.OK:
            return False
        else:
            resp_zip = 'resp_{}_{}.zip'.format(img_tag, f_or_p)
            handle = open(resp_zip, DependencyAnalyzerConstants.ZIPFILE_ACCESS_MODE)
            for chunk in response.iter_content(chunk_size=512):
                if chunk:  # filter out keep-alive new chunks
                    handle.write(chunk)
            handle.close()
            with zipfile.ZipFile(resp_zip, DependencyAnalyzerConstants.FILE_READ_MODE) as f:
                inner_dir = list({item.split(DependencyAnalyzerConstants.CHAR_SLASH)[0] for item in f.namelist()})[0]
            inner_dir = join(clone_location, inner_dir)
            cwd = os.getcwd()
            with zipfile.ZipFile(join(cwd, resp_zip), DependencyAnalyzerConstants.FILE_READ_MODE) as zip_ref:
                zip_ref.extractall(clone_location)
            for each_file in Path(inner_dir).glob('*.*'):
                trg_path = each_file.parent.parent
                each_file.rename(trg_path.joinpath(each_file.name))
            shutil.rmtree(inner_dir)
            if not self.generate_and_prepare_build_script(f_or_p, clone_location, repo_name):
                return False
            if not self.run_job_in_container(img_tag, clone_location, repo_name, f_or_p, op_path, img_tag):
                return False
            return True

    def generate_and_prepare_build_script(self, f_or_p, cloned_repo_dir, repo):
        """ Generate new build script using travis-build to reflect changes made to .travis.yml
            Modify build script to prevent git code checkout during build """
        travis_command = DependencyAnalyzerConstants.TRAVIS_COMPILE_BUILD_SCRIPT.format(join(expanduser(DependencyAnalyzerConstants.CHAR_TILDE),
                                                                                        DependencyAnalyzerConstants.TRAVIS_BUILD_LOCATION))
        cd_command = DependencyAnalyzerConstants.CHANGE_DIR_CMD.format(cloned_repo_dir)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(f'{cd_command}; {travis_command}')
        if not ok:
            print(stderr)
            print('Unable to generate travis build script')
            return False
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
                    if repo.startswith('okpy'):
                        lines.append(DependencyAnalyzerConstants.TRAVIS_PREVENT_GIT_CHECKOUT_CMD.format(f_or_p, repo.replace('okpy', 'Cal-CS-61A-Staff')))
                    else:
                        lines.append(DependencyAnalyzerConstants.TRAVIS_PREVENT_GIT_CHECKOUT_CMD.format(f_or_p, repo))
                else:
                    if not skip:
                        lines.append(line)

        # Overwrite the original build script with the modified build script.
        with open(build_script_path, DependencyAnalyzerConstants.FILE_WRITE_MODE) as f2:
            for l in lines:
                f2.write(l)
        return True

    def run_job_in_container(self, img_tag, repo_dir_path, repo_name, f_or_p, op_path, art):
        docker_container_cmd = DependencyAnalyzerConstants.DOCKER_RUN_IMAGE_CMD.format(img_tag
                                                                                       + DependencyAnalyzerConstants.CHAR_UNDERSCORE
                                                                                       + f_or_p, img_tag)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(docker_container_cmd)
        if not ok:
            print('Couldnt run container')
            print(stderr)
            return False
        get_container_id_cmd = DependencyAnalyzerConstants.DOCKER_GET_CONTAINER_ID_CMD\
                               + img_tag + DependencyAnalyzerConstants.CHAR_UNDERSCORE\
                               + f_or_p + DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE
        _, container_id, _, _ = DependencyAnalyzerUtils._run_command(get_container_id_cmd)
        build_script_path = join(repo_dir_path, DependencyAnalyzerConstants.GENERATED_BUILD_SCRIPT_NAME)
        cp_build_script_cmd = DependencyAnalyzerConstants.DOCKER_COPY_BUILD_SCRIPT_CMD\
            .format(build_script_path, container_id, f_or_p)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_build_script_cmd)
        if not ok:
            print('Failed to copy build script')
            print(stderr)
            return False
        if repo_name.startswith('okpy'):
            cp_repo_dir_cmd = DependencyAnalyzerConstants.DOCKER_COPY_SOURCE_CODE_CMD.format(repo_dir_path, container_id, f_or_p, repo_name.replace('okpy', 'Cal-CS-61A-Staff'))
        else:
            cp_repo_dir_cmd = DependencyAnalyzerConstants.DOCKER_COPY_SOURCE_CODE_CMD.format(repo_dir_path, container_id, f_or_p, repo_name)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_repo_dir_cmd)
        if not ok:
            print('Failed to copy source code')
            print(stderr)
            return False
        run_build_cmd = 'docker exec {} bash /usr/local/bin/run_{}.sh > {}/{}.{}.log 2>&1'.format(container_id, f_or_p, op_path, art, f_or_p)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(run_build_cmd)
        return True

    def bugsinpy_log_generation(self, proj_bug_ver, output_path, component_path):
        proj = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[0]
        bug = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[1]
        version = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[2]
        if proj == 'spacy':
            proj = 'spaCy'
        cloned_dir, python_version = self.setup_bug_repo(component_path, proj, bug, version)
        if not cloned_dir:
            print('Failed to clone repo')
            return False
        if not self.copy_build_script(component_path, cloned_dir, proj, bug, version):
            print('Failed to copy travis build script')
            return False
        if not self.execute_patch_changes(cloned_dir, output_path, proj, bug, version, python_version):
            print('Failed to execute build')
            return False
        self.bugsinpy_cleanup(proj, bug, version)
        return True

    def bugsinpy_cleanup(self, repo_name, bug_id, version):
        container_name = '{}_{}_{}'.format(repo_name, bug_id, version)
        cloned_dir = join(os.getcwd(), repo_name + DependencyAnalyzerConstants.CHAR_UNDERSCORE +
                         bug_id + DependencyAnalyzerConstants.CHAR_UNDERSCORE + version)
        if isdir(cloned_dir):
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo rm -rf {}'.format(cloned_dir))
        self.remove_docker_container(container_name)

    def setup_bug_repo(self, component_path, repo_name, bug_id, version):
        project_info_locn = join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR,
                                 repo_name, DependencyAnalyzerConstants.PROJECT_INFO_FILE_NAME)
        bug_info_locn = join(component_path,
                             DependencyAnalyzerConstants.PROJECTS_DIR,
                             repo_name, DependencyAnalyzerConstants.BUGS_DIR,
                             bug_id, DependencyAnalyzerConstants.BUG_INFO_FILENM)
        git_repo_url = self.get_value_from_info_file(project_info_locn, DependencyAnalyzerConstants.INFO_GIT_URL)
        if not git_repo_url:
            return None, None

        clone_dir = join(os.getcwd(), repo_name + DependencyAnalyzerConstants.CHAR_UNDERSCORE +
                         bug_id + DependencyAnalyzerConstants.CHAR_UNDERSCORE + version)
        if isdir(clone_dir):
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo rm -rf {}'.format(clone_dir))
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo mkdir {} && sudo chmod -R 777 {}'.format(clone_dir, clone_dir))

        git_clone_cmd = 'cd {} && git clone {}.git'.format(clone_dir, git_repo_url.strip(DependencyAnalyzerConstants.CHAR_SLASH))
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(git_clone_cmd)
        if not ok:
            print(stderr)
            print('Failed to clone repo')
            return None, None
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(clone_dir))
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.CHANGE_PERMISSION_CMD.format(join(clone_dir, repo_name)))
        if not ok:
            print(stderr)
            print('Failed to change permission for cloned repo')
            return None, None
        clone_dir = join(clone_dir, repo_name)
        failed_commit = self.get_value_from_info_file(bug_info_locn, DependencyAnalyzerConstants.INFO_BUGGY_COMMIT)
        passed_commit = self.get_value_from_info_file(bug_info_locn, DependencyAnalyzerConstants.INFO_FIXED_COMMIT)
        test_file_locn = self.get_value_from_info_file(bug_info_locn, DependencyAnalyzerConstants.INFO_TEST_FILE)
        python_version = self.get_value_from_info_file(bug_info_locn, DependencyAnalyzerConstants.INFO_PYTHON_VERSION)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('cd {} && git reset --hard {}'.format(clone_dir, passed_commit))
        if not ok:
            print(stderr)
            print('Failed to reset head of cloned repo to passed commit')
            return None, None
        if version == 0:  # failed version
            test_file_contents = self.get_test_file_contents(clone_dir, test_file_locn)
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('cd {} && git reset --hard {}'.format(clone_dir, failed_commit))
            if not ok:
                print(stderr)
                print('Failed to reset head of cloned repo to failed commit')
                return None, None
            self.write_test_file_contents(clone_dir, test_file_locn, test_file_contents)
        return clone_dir, python_version

    def get_value_from_info_file(self, info_file_path, start_key):
        if not isfile(info_file_path):
            return None
        with open(info_file_path, DependencyAnalyzerConstants.FILE_READ_MODE) as f:
            info_file_contents = [x.strip() for x in f.readlines()]
        for line in info_file_contents:
            if line.startswith(start_key):
                return line.split(start_key)[-1].strip(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE)
        return None

    def get_test_file_contents(self, clone_dir, test_file_locn):
        test_file_contents = None
        with open(join(clone_dir, test_file_locn), DependencyAnalyzerConstants.FILE_READ_MODE) as f:
            test_file_contents = [x.strip() for x in f.readlines()]
        return test_file_contents

    def write_test_file_contents(self, clone_dir, test_file_locn, test_file_contents):
        with open(join(clone_dir, test_file_locn), DependencyAnalyzerConstants.FILE_WRITE_MODE) as f:
            f.write('\n'.join(test_file_contents))

    def copy_build_script(self, travis_files_path, cloned_dir, repo_name, bug_id, version):
        if not isdir(join(travis_files_path, 'travis_scripts_store')):
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo mkdir {}'.format(join(travis_files_path, 'travis_scripts_store')))
            if not ok:
                print(stderr)
                return False
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo chmod -R 777 {}'.format(join(travis_files_path, 'travis_scripts_store')))
        if not isdir(join(travis_files_path, 'travis_scripts_store', '{}_{}_{}'.format(repo_name, bug_id, version))):
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo mkdir {}'.format(join(travis_files_path, 'travis_scripts_store', '{}_{}_{}'.format(repo_name, bug_id, version))))
            if not ok:
                print(stderr)
                return False
            _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('sudo chmod -R 777 {}'.format(join(travis_files_path, 'travis_scripts_store', '{}_{}_{}'.format(repo_name, bug_id, version))))
        travis_gen = TravisYMLGenerator()
        travis_gen.bugsinpy_yaml_generation('{}_{}_{}'.format(repo_name, bug_id, version), travis_files_path, join(travis_files_path, 'travis_scripts_store'), False)
        cp_travis_yml_cmd = 'cp {}/travis_scripts_store/{}_{}_{}/.travis.yml {}'.format(travis_files_path, repo_name, bug_id, version, cloned_dir)
        cp_travis_script_cmd = 'cp {}/travis_scripts_store/{}_{}_{}/test.sh {}'.format(travis_files_path, repo_name, bug_id, version, cloned_dir)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(DependencyAnalyzerConstants.CHAR_SEMI_COLON.join([cp_travis_yml_cmd, cp_travis_script_cmd]))
        if not ok:
            print(stderr)
            return False
        return True

    def execute_patch_changes(self, cloned_repo_dir, output_log_path, repo_name, bug_id, version, python_ver):
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
            print(stderr)
            print('Failed to run Docker container')
            return False
        get_container_id_cmd = DependencyAnalyzerConstants.DOCKER_GET_CONTAINER_ID_CMD + \
            container_name + DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE
        _, container_id, stderr, _ = DependencyAnalyzerUtils._run_command(
            get_container_id_cmd)
        copy_source_code_cmd = DependencyAnalyzerConstants.DOCKER_CP_HOME_CMD.format(
            cloned_repo_dir, container_id)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            copy_source_code_cmd)
        if not ok:
            print(stderr)
            print('Failed to copy source code')
            return False
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
            print(stderr)
            print('Failed to copy build log')
            return False
        self.remove_docker_container(container_name)
        return True

    def remove_docker_container(self, container_name):
        """ Remove Docker container used """
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(
            DependencyAnalyzerConstants.DOCKER_REMOVE_CONTAINER.format(container_name))
