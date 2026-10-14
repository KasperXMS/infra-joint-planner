ARG TASK_IMAGE
FROM model-aware-codex-runtime:0.162.1 AS codex_runtime
FROM ${TASK_IMAGE}
COPY --from=codex_runtime /usr/local /usr/local
