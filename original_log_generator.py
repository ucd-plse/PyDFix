import os
from os.path import join, isfile
from bugswarm.common.log_downloader import download_log
from dependency_analyzer_const import DependencyAnalyzerConstants
from dependency_analyzer_utils import DependencyAnalyzerUtils


class OriginalLogGenerator:
    def __init__(self, dataset_idx):
        self._dataset_idx = dataset_idx
        self._orig_content = None

    def start_log_gen(self, id, output_path, orig_file_name=None, component_path=None):
        if self._dataset_idx == 1 and not self._orig_content:
            self._orig_content = self.bugswarm_log_download(id, output_path, orig_file_name)
        elif not self._orig_content:
                self._orig_content = self.bugsinpy_log_generation(id, output_path, component_path)
        return self._orig_content

    def bugswarm_log_download(self, orig_id, orig_log_path, orig_file_name):
        """ Download original logs from TravisCI """
        downloaded = False
        orig_content = None
        downloaded = download_log(orig_id, join(orig_log_path, orig_file_name))

        if downloaded:
            # fetching contents of original log
            with open(join(orig_log_path, orig_file_name),
                      encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
                orig_content = [x.strip() for x in f.readlines()]
        return orig_content

    def bugsinpy_log_generation(self, proj_bug_ver, output_path, component_path):
        proj = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[0]
        bug = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[1]
        version = proj_bug_ver.split(DependencyAnalyzerConstants.CHAR_UNDERSCORE)[2]
        test_cmds = []
        with open(join(component_path, DependencyAnalyzerConstants.PROJECTS_DIR, proj, DependencyAnalyzerConstants.BUGS_DIR, bug, 'run_test.sh'), DependencyAnalyzerConstants.FILE_READ_MODE, encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
            test_cmds = [x.strip(DependencyAnalyzerConstants.CHAR_NEW_LINE).strip() for x in f.readlines()]
        shell_cmd = 'cd {} && (bugsinpy-checkout -p {} -i {} -v {} && cd {}/framework/bin/temp/{} && bugsinpy-compile && {}) > orig-failed-{}-{}-{}-log.log 2>&1'.format(component_path, proj, bug, version, component_path, proj, DependencyAnalyzerConstants.CHAR_SEMI_COLON.join(test_cmds), proj, bug, version)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(shell_cmd, env=os.environ)
        if not isfile(join(component_path, 'orig-failed-{}-{}-{}-log.log'.format(proj, bug, version))):
            print('Failed to generate failed orig log')
            print(stderr)
            print(stdout)
            return None
        cp_failed_log_cmd = 'cp {}/orig-failed-{}-{}-{}-log.log {}/{}_{}_{}_orig.log'.format(component_path, proj, bug,  version, output_path, proj, bug, version)
        _, stdout, stderr, ok = DependencyAnalyzerUtils._run_command(cp_failed_log_cmd)
        if not ok:
            print(stderr)
            print('Failed to copy failed original log')
            return None
        orig_content = None
        if isfile(join(component_path, 'orig-failed-{}-{}-{}-log.log').format(proj, bug, version)):
            with open(join(component_path, 'orig-failed-{}-{}-{}-log.log').format(proj, bug, version),
                      encoding=DependencyAnalyzerConstants.STR_ENCODING_UTF8) as f:
                orig_content = [x.strip() for x in f.readlines()]
            os.remove(join(component_path, 'orig-failed-{}-{}-{}-log.log'.format(proj, bug, version)))
        return orig_content
