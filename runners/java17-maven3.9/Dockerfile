FROM eclipse-temurin:17-jdk-jammy

# ---------- metadata ----------
LABEL name="runner-java17-maven39"
LABEL description="Fat runner for Spring Boot + Maven CI pipelines"
LABEL java.version="17"
LABEL maven.version="3.9.12"

# ---------- system deps ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        unzip \
        ca-certificates \
        bash \
        python3 \
        python3-pip \
        pipx && \
    rm -rf /var/lib/apt/lists/*

# --- pipx env (required for  semgrep , tried other methods and this is the simplest so far ) -----
ENV PIPX_HOME=/opt/pipx
ENV PIPX_BIN_DIR=/usr/local/bin
ENV PATH=/usr/local/bin:$PATH

# ---------- semgrep ----------
RUN pipx install semgrep && \
    semgrep --version

# ---------- gitleaks install ----------
COPY gitleaks /usr/local/bin/gitleaks
RUN chmod +x /usr/local/bin/gitleaks

# ---------- trivy ----------
# latest version last time i checked 
ENV TRIVY_VERSION=0.68.2 
RUN curl -fsSL https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_0.68.2_Linux-64bit.tar.gz \
    -o /tmp/trivy.tar.gz && \
    tar -xzvf /tmp/trivy.tar.gz -C /tmp && \
    mv /tmp/trivy /usr/local/bin/trivy && \
    chmod +x /usr/local/bin/trivy && \
    rm /tmp/trivy.tar.gz

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
