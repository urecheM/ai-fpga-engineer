# hdleval — reproducible research platform image.
# A fresh environment can execute the full pipeline with only:
#   docker build -t hdleval .
#   docker run --rm hdleval            # runs reproduce.py end-to-end
#
# The image installs the open-source HDL toolchain (GHDL + Yosys +
# ghdl-yosys-plugin) so the compile/synthesis/simulation stages run for real,
# not 'skipped'.
FROM python:3.11-slim AS base

ARG OSS_CAD_SUITE_TAG=2026-07-09

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HDLEVAL_REQUIRE_TOOLS=0 \
    PATH="/opt/oss-cad-suite/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git make libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    stamp="$(echo "$OSS_CAD_SUITE_TAG" | tr -d '-')"; \
    curl -fsSL --retry 3 --retry-delay 5 \
      "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${OSS_CAD_SUITE_TAG}/oss-cad-suite-linux-x64-${stamp}.tgz" \
      -o /tmp/oss-cad-suite.tgz; \
    tar -xzf /tmp/oss-cad-suite.tgz -C /opt; \
    rm -f /tmp/oss-cad-suite.tgz; \
    yosys --version; ghdl --version

WORKDIR /opt/hdleval
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e ".[dev]" || pip install pyyaml

COPY . .

RUN python scripts/check_toolchain.py

# deterministic default entrypoint: reproduce every artifact
CMD ["python", "reproduce.py"]
