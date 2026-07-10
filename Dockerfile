# hdleval — reproducible research platform image.
# A fresh environment can execute the full pipeline with only:
#   docker build -t hdleval .
#   docker run --rm hdleval            # runs reproduce.py end-to-end
#
# The image installs the open-source HDL toolchain (GHDL + Yosys) so the
# compile/synthesis/simulation stages run for real, not 'skipped'.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HDLEVAL_REQUIRE_TOOLS=0

# --- system HDL toolchain (best-effort; pipeline degrades gracefully) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        ghdl yosys git make \
    && rm -rf /var/lib/apt/lists/* || true

WORKDIR /opt/hdleval
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e ".[dev]" || pip install pyyaml

COPY . .

# deterministic default entrypoint: reproduce every artifact
CMD ["python", "reproduce.py"]
