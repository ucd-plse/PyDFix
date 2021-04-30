#!/usr/bin/env bash

WORKING_DIR="$PWD"
echo $WORKING_DIR
sudo usermod -aG docker $USER
sudo setfacl -m user:$USER:rw /var/run/docker.sock

print_green 'Install BugSwarm'
git clone https://github.com/BugSwarm/bugswarm.git
sudo cp credentials.py bugswarm/bugswarm/common
cd "${WORKING_DIR}"/bugswarm && sed -i 's/ --user//' provision.sh && source provision.sh
echo $WORKING_DIR
echo $PWD
cd $WORKING_DIR/bugswarm && sudo chmod -R 777 setup.py && pip3 install .
exit_if_failed 'Installing BugSwarm failed'

print_green 'Install BugsInPy'
cd ..
git clone https://github.com/soarsmu/BugsInPy.git
echo ${WORKING_DIR}
echo $PWD
echo "export PATH=$PATH:"${WORKING_DIR}"/BugsInPy/framework/bin" >> ~/.bashrc
exit_if_failed 'Installing BugsInPy failed'
echo "Completed BugsInPy setup"
