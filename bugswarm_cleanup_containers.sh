docker rm -f $(docker ps --all | grep bugswarm/images | awk '{print $1}')
