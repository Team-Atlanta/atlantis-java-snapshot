FROM openjdk:17-jdk-slim AS base

RUN apt-get update && apt-get install -y \
    wget \
    git
RUN rm -rf /var/lib/apt/lists/*

# Download and install Maven 3.9.9
RUN wget https://dlcdn.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz \
    && tar xf apache-maven-3.9.9-bin.tar.gz \
    && mv apache-maven-3.9.9 /usr/share/maven \
    && rm apache-maven-3.9.9-bin.tar.gz

# Set Maven environment variables
ENV MAVEN_HOME=/usr/share/maven
ENV PATH=${MAVEN_HOME}/bin:${PATH}

FROM base AS dev
ENTRYPOINT ["tail", "-f", "/dev/null"]
