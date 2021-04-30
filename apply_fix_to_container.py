import sys
import subprocess


def main(argv=None):
    if argv is None:
        argv = sys.argv

    f_or_p, repo_dir_name, build_script_name = _validate_input(argv)
    execute_build_script(f_or_p)


def execute_build_script(f_or_p):
    _, stdout, stderr, ok = _run_command('sudo chmod -R 777 /home')
    _, stdout, stderr, ok = _run_command('bash /usr/local/bin/run_{}.sh > /home/travis/log-{}.log 2>&1'.format(f_or_p, f_or_p))


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok


def _validate_input(argv):
    if len(argv) != 4:
        print('Too few arguments')
        sys.exit(1)
    f_or_p = argv[1]
    repo_dir_name = argv[2]
    build_script_name = argv[3]
    return f_or_p, repo_dir_name, build_script_name


if __name__ == '__main__':
    sys.exit(main())
