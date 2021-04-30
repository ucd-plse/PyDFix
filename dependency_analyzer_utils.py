from os.path import isdir, isfile, join
import csv
import json
import subprocess
import re
from error_type import ErrorType
from dependency_analyzer_const import DependencyAnalyzerConstants


class DependencyAnalyzerUtils:
    @staticmethod
    def valid_input(args, usage):
        """ Validate input with -path option"""
        valid = False
        if len(args) != 5 and len(args) != 3:
            DependencyAnalyzerUtils.print_usage('Too few arguments.', usage)
        elif args[1] != '-path':
            DependencyAnalyzerUtils.print_usage('Does not contain path option', usage)
        elif not isdir(args[2]):
            DependencyAnalyzerUtils.print_usage('Not a valid directory', usage)
        elif len(args) == 5 and args[3] != '-filename':
            DependencyAnalyzerUtils.print_usage('Invalid option', usage)
        elif len(args) == 5 and not isfile(join(args[2], args[4])):
            DependencyAnalyzerUtils.print_usage('Invalid file name', usage)
        else:
            valid = True
        return valid

    @staticmethod
    def valid_input_docker_script(args, usage):
        """ Validate input with -path and -output options"""
        valid = False
        if len(args) < 5:
            DependencyAnalyzerUtils.print_usage('Too few arguments.', usage)
        elif args[1] != '-path':
            DependencyAnalyzerUtils.print_usage('Does not contain path option', usage)
        elif not isdir(args[2]):
            DependencyAnalyzerUtils.print_usage('Not a valid -path directory', usage)
        elif args[3] != '-output':
            DependencyAnalyzerUtils.print_usage('Does not contain output option', usage)
        elif not isdir(args[4]):
            DependencyAnalyzerUtils.print_usage('Not a valid -output directory', usage)
        else:
            valid = True

        if len(args) == 6 and args[5] != '-all-artifacts':
            DependencyAnalyzerUtils.print_usage('Incorrect optional arguments. ', usage)
            valid = False
        return valid

    @staticmethod
    def valid_reproduce_input(args, usage):
        """ Validate input with -path, -output and -component options"""
        valid = False
        if len(args) < 7:
            DependencyAnalyzerUtils.print_usage('Too few arguments.', usage)
        elif args[1] != '-path':
            DependencyAnalyzerUtils.print_usage('Does not contain path option', usage)
        elif not isdir(args[2]):
            DependencyAnalyzerUtils.print_usage('Not a valid -path directory', usage)
        elif args[3] != '-output':
            DependencyAnalyzerUtils.print_usage('Does not contain output option', usage)
        elif not isdir(args[4]):
            DependencyAnalyzerUtils.print_usage('Not a valid -output directory', usage)
        elif args[5] != '-component':
            DependencyAnalyzerUtils.print_usage('Does not contain component option', usage)
        elif not isdir(args[6]):
            DependencyAnalyzerUtils.print_usage('Not a valid -component directory', usage)
        else:
            valid = True
        return valid

    @staticmethod
    def valid_iterative_solver_input(args, usage):
        """ Validate input to automat_iterative_dependency_solve.py """
        valid = False
        if len(args) < 7:
            DependencyAnalyzerUtils.print_usage('Too few arguments.', usage)
        elif len(args) > 7:
            DependencyAnalyzerUtils.print_usage('Too many arguments.', usage)
        elif args[1] != '-path':
            DependencyAnalyzerUtils.print_usage('Does not contain path option', usage)
        elif args[3] != '-sourcecode':
            DependencyAnalyzerUtils.print_usage('Does not contain sourcecode option', usage)
        elif args[5] != '-intermediate':
            DependencyAnalyzerUtils.print_usage('Does not contain intermediate option', usage)
        elif not isdir(args[2]):
            DependencyAnalyzerUtils.print_usage('Not a valid -path directory', usage)
        elif not isdir(args[4]):
            DependencyAnalyzerUtils.print_usage('Not a valid -sourcecode directory', usage)
        elif not isdir(args[6]):
            DependencyAnalyzerUtils.print_usage('Not a valid -intermediate directory', usage)
        else:
            valid = True
        return valid

    @staticmethod
    def print_usage(err_msg, usage):
        """Print usage and error message"""
        print(usage)
        print('Error: ' + err_msg)

    @staticmethod
    def print_error_msg(stderr, msg, cmd):
        print(stderr)
        print(msg)
        print('FAILED command: {}'.format(cmd))

    @staticmethod
    def write_to_csv(rows, headers, file_nm):
        """Write to csv"""
        with open(file_nm, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)

    @staticmethod
    def get_artifact_dict(path):
        artifacts = []
        img_tag_dict = {}
        with open(join(path, 'artifacts.json'), 'r') as f:
            artifacts = json.load(f)
        for art in artifacts:
            img_tag_dict[art['image_tag']] = art
        return img_tag_dict

    @staticmethod
    def _run_command(command, env=None):
        if env:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=env)
        else:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        stdout = stdout.decode('utf-8').strip()
        stderr = stderr.decode('utf-8').strip()
        ok = process.returncode == 0
        return process, stdout, stderr, ok

    @staticmethod
    def check_matches(line):
        match_type = None
        for err_type in ErrorType:
            match_obj = re.search(
                DependencyAnalyzerConstants.INEXACT_PATTERN_LIST[err_type], line, re.M)
            if match_obj:
                exact_match = re.search(
                    DependencyAnalyzerConstants.ERROR_PATTERN_LIST[err_type], line, re.M)
                if exact_match:
                    match_type = err_type
                    break
        return match_type
