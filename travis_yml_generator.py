from os.path import join, isfile
import yaml
from os import chdir, getcwd
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils
from collections import OrderedDict


class TravisYMLGenerator:
    def __init__(self):
        return

    def bugsinpy_yaml_generation(self, proj_bug_ver, component_path, output_path, with_patch):
        proj = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[0]
        bug = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[1]
        version = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[2]
        python_version = None
        python_path = None
        buggy_commit_sha = None
        author = None
        with open(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR,
                       proj, DependencyAnalyzerConstants.PROJECT_INFO_FILE_NAME),
                  DependencyAnalyzerConstants.FILE_READ_MODE) as f:
            proj_info_file_contents = [x.strip() for x in f.readlines()]
        for line in proj_info_file_contents:
            if line.startswith(DependencyAnalyzerConstants.INFO_GIT_URL):
                author = line.split(DependencyAnalyzerConstants.INFO_GIT_URL)[-1].split(DependencyAnalyzerConstants.CHAR_SLASH)[-2]
        with open(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, proj,
                       DependencyAnalyzerConstants.BUGS_DIR, bug, DependencyAnalyzerConstants.BUG_INFO_FILENM),
                  DependencyAnalyzerConstants.FILE_READ_MODE) as f:
            info_file_contents = [x.strip() for x in f.readlines()]
        for line in info_file_contents:
            if line.startswith(DependencyAnalyzerConstants.INFO_PYTHON_VERSION):
                python_version = line.split(DependencyAnalyzerConstants.INFO_PYTHON_VERSION)[-1].strip().strip(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE)
            if line.startswith(DependencyAnalyzerConstants.INFO_BUGGY_COMMIT):
                buggy_commit_sha = line.split(DependencyAnalyzerConstants.INFO_BUGGY_COMMIT)[-1].strip()
            if line.startswith(DependencyAnalyzerConstants.INFO_PYTHON_PATH):
                python_path = line.split(DependencyAnalyzerConstants.INFO_PYTHON_PATH)[-1].strip()
        if not python_version or not buggy_commit_sha:
            print('Could not extract info from bug.info for {} bug {}'.format(proj, bug))
            return False
        setup_steps = None
        if isfile(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, proj,
                       DependencyAnalyzerConstants.BUGS_DIR, bug, DependencyAnalyzerConstants.SETUP_SH_FILE_NAME)):
            with open(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, proj,
                           DependencyAnalyzerConstants.BUGS_DIR, bug, DependencyAnalyzerConstants.SETUP_SH_FILE_NAME),
                      DependencyAnalyzerConstants.FILE_READ_MODE) as f:
                setup_steps = [x.strip() for x in f.readlines()]
            if not setup_steps:
                print('Could not extract info from setup.sh for {} bug {}'.format(proj, bug))
                return False
        test_steps = None
        with open(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, proj,
                       DependencyAnalyzerConstants.BUGS_DIR, bug, DependencyAnalyzerConstants.RUN_TEST_SH_FILE_NAME),
                  DependencyAnalyzerConstants.FILE_READ_MODE) as f:
            test_steps = [x.strip() for x in f.readlines()]
        if not test_steps:
            print('Could not extract info from run_test.sh for {} bug {}'.format(proj, bug))
            return False
        travis_dict = OrderedDict()
        travis_dict[DependencyAnalyzerConstants.TRAVIS_LANGUAGE] = DependencyAnalyzerConstants.LANGUAGE_PYTHON_LOWERCASE
        travis_dict[DependencyAnalyzerConstants.LANGUAGE_PYTHON_LOWERCASE] = python_version
        if python_path:
            travis_dict[DependencyAnalyzerConstants.TRAVIS_ENV] = 'PATH={}/framework/bin/temp/{}:$PATH'.format(component_path, python_path.replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                                                                                                  DependencyAnalyzerConstants.CHAR_EMPTY))
        travis_dict[DependencyAnalyzerConstants.TRAVIS_BEFORE_INSTALL] = ['sudo chmod -R 777 /home',
                                            'sudo chmod -R 777 /home/docker', 'sudo chown -R root /home/docker', 'cd /home/{}'.format(proj),
                                            'python -m pip install --user virtualenv',
                                            'virtualenv -p python{} venv'.format(python_version.replace(DependencyAnalyzerConstants.CHAR_DOUBLE_QUOTE,
                                                                                                        DependencyAnalyzerConstants.CHAR_EMPTY)),
                                            'source venv/bin/activate']
        if with_patch:
            travis_dict[DependencyAnalyzerConstants.TRAVIS_BEFORE_INSTALL].append('pip install -r patch_requirements.txt --no-deps')
        if setup_steps:
            travis_dict[DependencyAnalyzerConstants.TRAVIS_INSTALL] = setup_steps
        travis_dict[DependencyAnalyzerConstants.TRAVIS_SCRIPT] = test_steps
        yaml.add_representer(OrderedDict, TravisYMLGenerator.ordered_dict_representer)
        with open(join(output_path, '{}_{}_{}'.format(proj, bug, version), '.travis.yml'), DependencyAnalyzerConstants.FILE_WRITE_PLUS_MODE) as f:
            yaml.dump(travis_dict, f, default_flow_style=False)
        return self.generate_build_script(join(output_path, '{}_{}_{}'.format(proj, bug, version)))

    @staticmethod
    def ordered_dict_representer(self, value):
        return self.represent_mapping('tag:yaml.org,2002:map', value.items())

    def generate_build_script(self, dir_locn):
        cwd = getcwd()
        chdir(dir_locn)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command('~/.travis/travis-build/bin/travis compile > test.sh')

        if not ok:
            print(stderr)
            return False
        lines = []

        with open(join(dir_locn, DependencyAnalyzerConstants.GENERATED_BUILD_SCRIPT_NAME),
                  DependencyAnalyzerConstants.FILE_READ_MODE) as f:
            activate_virtual_env = 'travis_cmd source\\ \\~/virtualenv/python'
            skip = False
            for line in f:
                activate_virtual_env = 'travis_cmd source\\ \\~/virtualenv/python'
                if activate_virtual_env in line:
                    continue
                elif DependencyAnalyzerConstants.TRAVIS_START_GIT_CHECKOUT_CMD in line:
                    skip = True
                elif DependencyAnalyzerConstants.TRAVIS_END_GIT_CHECKOUT_CMD in line:
                    skip = False
                else:
                    if not skip:
                        if 'travis_host_os=' in line:
                            lines.append(line.split('=')[0] + "='ubuntu'\n")
                        elif 'travis_rel_version=' in line:
                            lines.append(line.split('=')[0] + "='20.04'\n")
                        else:
                            lines.append(line)
        # Overwrite the original build script with the modified build script.
        with open(join(dir_locn, DependencyAnalyzerConstants.GENERATED_BUILD_SCRIPT_NAME),
                  DependencyAnalyzerConstants.FILE_WRITE_MODE) as f2:
            for l in lines:
                f2.write(l)
        chdir(cwd)
        return True

