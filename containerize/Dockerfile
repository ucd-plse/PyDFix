FROM ubuntu:20.04
RUN apt-get update && apt-get install -y git sudo gnupg \
	vim nano tmux screen less python3 zip wget curl acl python3-venv dos2unix python-is-python3 && \
	groupadd rvm && groupadd docker && \
	wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | \
	sudo apt-key add - && \
	echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu" \
		"focal/mongodb-org/4.4 multiverse" | \
		sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list && \
	sudo apt-get update && \
	sudo apt-get install mongodb-org-shell && \
	useradd pydfix && \
	sudo usermod -aG rvm,docker pydfix && \
	chsh pydfix -s /bin/bash && \
	echo pydfix ALL=NOPASSWD:ALL | sudo tee -a /etc/sudoers && \
	mkdir /home/pydfix && chown pydfix /home/pydfix && \
	chown -R pydfix /usr/local/lib/python3.8/ && \
	ln -snf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
	echo America/Los_Angeles > /etc/timezone

USER pydfix
RUN cd /home/pydfix; git clone https://github.com/ucd-plse/PyDFix.git
WORKDIR /home/pydfix/PyDFix
RUN sudo su pydfix -c ./provision.sh && \
	echo "source /etc/profile.d/rvm.sh" >> /home/pydfix/.bashrc && \
	echo "source ~/.bashrc" >> /home/pydfix/.bash_profile
