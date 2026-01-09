FROM eclipse-temurin:17-jdk-jammy

# ---------- metadata ----------
LABEL name="runner-java17-gradle8"
LABEL description="Fat runner for Spring Boot + Gradle CI pipelines"
LABEL java.version="17"
LABEL gradle.version="8.7"

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

# ---------- gradle install ----------
ENV GRADLE_VERSION=8.7
ENV GRADLE_HOME=/opt/gradle
ENV PATH=$GRADLE_HOME/bin:$PATH

RUN curl -fsSL https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip \
    -o /tmp/gradle.zip && \
    unzip /tmp/gradle.zip -d /opt && \
    mv /opt/gradle-${GRADLE_VERSION} ${GRADLE_HOME} && \
    rm /tmp/gradle.zip

# ---------- non-root user ----------
RUN useradd -m -u 10001 runner
USER runner
WORKDIR /home/runner

CMD ["bash"]

