import sys
  
# DockerHub
DOCKER_HUB_REPO = 'as'
DOCKER_HUB_CACHED_REPO = 'as'
DOCKER_HUB_USERNAME = 'as'
DOCKER_HUB_PASSWORD = 'as'
if not DOCKER_HUB_REPO:
    print('[ERROR]: DOCKER_HUB_REPO has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
if not DOCKER_HUB_CACHED_REPO:
    print('[WARNING]: DOCKER_HUB_CACHED_REPO has not been found. Skip caching dependencies in reproducing stage.')
if not DOCKER_HUB_USERNAME:
    print('[ERROR]: DOCKER_HUB_USERNAME has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
if not DOCKER_HUB_PASSWORD:
    print('[ERROR]: DOCKER_HUB_PASSWORD has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')

# Docker Private Registry
DOCKER_REGISTRY_REPO = 'as'
DOCKER_REGISTRY_USERNAME = 'as'
DOCKER_REGISTRY_PASSWORD = 'as'
if not DOCKER_REGISTRY_REPO:
    print('[WARNING]: DOCKER_REGISTRY_REPO has not been found. Skip pushing to docker private registry '
          'in reproducing stage')
if not DOCKER_REGISTRY_USERNAME:
    print('[WARNING]: DOCKER_REGISTRY_USERNAME has not been found. Skip pushing to docker private registry '
          'in reproducing stage')
if not DOCKER_REGISTRY_PASSWORD:
    print('[WARNING]: DOCKER_REGISTRY_PASSWORD has not been found. Skip pushing to docker private registry '
          'in reproducing stage')

# GitHub
# These GitHub tokens are hard-coded and can be used for token switching to minimize the time spent waiting for our
# GitHub quota to reset.
GITHUB_TOKENS = ['c9be24c63897a08957e2618c8d7076343d66fd92']
if not GITHUB_TOKENS:
    print('[ERROR]: GITHUB_TOKENS has not been set. Please input your credentials under common/credentials.py and '
          'rerun the bugswarm/provision.sh script.')
    sys.exit(1)

# Travis CI Access Token for sending authenticated requests up to 2000/min
# Unauthenticated requests are up to 500/min
TRAVIS_TOKENS = []

# Authentication tokens for the database.
DATABASE_PIPELINE_TOKEN = 'THFk1qAAMburDyXS6vYk2kiaHWn6MiPgT8TYrNHISWA'
if not DATABASE_PIPELINE_TOKEN:
    print('[ERROR]: DATABASE_PIPELINE_TOKEN has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
    sys.exit(1)

COMMON_HOSTNAME = 'www.api.bugswarm.org'