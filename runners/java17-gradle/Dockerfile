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
        bash && \
    rm -rf /var/lib/apt/lists/*

#semgrep 
RUN snap install semgrep

# ---------- gitleaks install ----------
COPY gitleaks /usr/local/bin/gitleaks
RUN chmod +x /usr/local/bin/gitleaks

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
