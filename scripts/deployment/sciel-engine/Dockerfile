ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS python_environment
COPY wheelhouse/ /wheelhouse/
COPY requirements.lock /requirements.lock
RUN python -m venv /opt/venv && \
    /opt/venv/bin/python -m pip install --no-index --find-links=/wheelhouse --require-hashes -r /requirements.lock
COPY sciel/ /build/sciel/
RUN /opt/venv/bin/python -m pip install --no-index --no-build-isolation --no-deps /build/sciel && \
    /opt/venv/bin/python -m pip check

FROM ${BASE_IMAGE}
ARG SCIEL_COMMIT
ARG ENGINE_VERSION
ARG ARENA_SNAPSHOT_SHA256
LABEL org.opencontainers.image.title="SCiEL private Arena engine" \
      org.opencontainers.image.version="${ENGINE_VERSION}" \
      org.opencontainers.image.revision="${SCIEL_COMMIT}" \
      org.opencontainers.image.source="https://github.com/Doldrums/sciel" \
      io.arena.sciel.contract="sciel-cli-v1" \
      org.empira.arena.snapshot-sha256="${ARENA_SNAPSHOT_SHA256}"
COPY --from=python_environment /opt/venv/ /opt/venv/
COPY sciel/ /opt/sciel/
COPY arena/ /opt/arena/
COPY git /usr/local/bin/git
COPY docker /usr/local/bin/docker
COPY git-COPYING /usr/local/share/licenses/git/COPYING
COPY requirements.lock build-inputs.json /opt/arena-build/
ENV PATH="/opt/venv/bin:/usr/local/bin:/usr/bin:/bin" \
    PYTHONPATH="/opt/sciel/src:/opt/arena/src" \
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    USER=arena LOGNAME=arena HOME=/tmp/arena-home
RUN mkdir -p /run/arena-engine /arena-input /srv/arena/sources /srv/arena/control/runs && \
    chmod 0755 /run/arena-engine /arena-input /srv/arena/sources /srv/arena/control/runs && \
    git config --system --add safe.directory /opt/sciel && \
    /opt/venv/bin/python -c "import sciel, arena.frameworks.evaluation, torch; assert torch.__version__ == '2.14.0+cpu'" && \
    /opt/venv/bin/python -c "from arena.registry import get_catalog; from arena.task_library import resolve_task_root, verify_task_library; [verify_task_library(resolve_task_root(source=s), s) for s in get_catalog()['sources']]" && \
    git --version && docker --version
WORKDIR /opt/sciel
USER 998:998
ENTRYPOINT ["/opt/venv/bin/python", "-m", "sciel.cli.main"]
