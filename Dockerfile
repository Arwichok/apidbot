ARG python=python:3.10-alpine3.16


# build stage
FROM ${python} AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /project/
COPY apidbot/ project/apidbot/

# install dependencies and project into the local packages directory
WORKDIR /project
RUN mkdir __pypackages__ && pdm install --prod --no-lock --no-editable


# run stage
FROM ${python}

# retrieve packages from build stage
ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/__pypackages__/3.10/lib /project/pkgs

# set command/entrypoint, adapt to fit your needs
CMD ["python", "-m", "apidbot"]
