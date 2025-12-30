FROM eclipse-temurin:17-jdk-jammy

# ---------- metadata ----------
LABEL name="runner-java17-maven39"
LABEL description="Fat runner for Spring Boot + Maven CI pipelines"
LABEL java.version="17"
LABEL maven.version="3.9.12"

# ---------- system deps ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        unzip \
        ca-certificates \
        bash && \
    rm -rf /var/lib/apt/lists/*

# ---------- maven install ----------
ENV MAVEN_VERSION=3.9.12
ENV MAVEN_HOME=/opt/maven
ENV PATH=$MAVEN_HOME/bin:$PATH

RUN curl -fsSL https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/${MAVEN_VERSION}/apache-maven-${MAVEN_VERSION}-bin.zip \
    -o /tmp/maven.zip && \
    unzip /tmp/maven.zip -d /opt && \
    mv /opt/apache-maven-${MAVEN_VERSION} ${MAVEN_HOME} && \
    rm /tmp/maven.zip

# ---------- non-root user ----------
RUN useradd -m -u 10001 runner
USER runner
WORKDIR /home/runner

# ---------- runtime expectations ----------
# /app       -> mounted read-only
# /reports   -> mounted writable
# /pipelines -> mounted read-only

CMD ["bash"]
