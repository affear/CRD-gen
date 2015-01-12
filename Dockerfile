FROM ubuntu:latest
MAINTAINER affearteam

ADD bin/ /oscard/bin
ADD oscard/ /oscard/oscard
ADD oscard.conf /oscard/
ADD requirements.txt /oscard/

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y python python-pip
# extra requirements for pip install
RUN apt-get install -y python-dev libffi-dev libssl-dev
RUN apt-get upgrade -y
RUN pip install -r /oscard/requirements.txt

ENV PYTHONPATH /oscard/
WORKDIR /oscard
RUN mkdir logs

CMD ./bin/run_proxy
#TODO add the collector too