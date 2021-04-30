DOCKER_GID=`stat -c %g /var/run/docker.sock`
sudo groupadd -g $DOCKER_GID docker_host
sudo usermod -aG $DOCKER_GID pydfix
