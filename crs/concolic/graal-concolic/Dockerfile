FROM ubuntu:20.04 as base
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    python3.9 \
    python3-pip \
    git

FROM base as espresso-dev
COPY mx /mx
ENV PATH="$PATH:/mx"
RUN echo Y | mx fetch-jdk labsjdk-ce-21
RUN python3 -mpip install ninja_syntax
RUN apt-get install -y zip
RUN apt-get install -y wget

WORKDIR /graal-jdk
RUN wget https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-linux-x86_64.tar.gz
RUN tar -xzvf cmake-3.31.6-linux-x86_64.tar.gz
RUN cp -r cmake-3.31.6-linux-x86_64/* /usr/
RUN rm -rf cmake-3.31.6-linux-x86_64

WORKDIR /graal-jdk

COPY docker-scripts /docker-scripts
RUN chmod +x /docker-scripts/*

ENTRYPOINT ["/docker-scripts/init_dev.sh"]
