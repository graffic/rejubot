FROM python:3.11-alpine AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /project/
COPY src/ /project/src

# install dependencies and project into the local packages directory
WORKDIR /project
RUN mkdir __pypackages__ && pdm sync --prod --no-editable

FROM python:3.11-alpine

RUN apk add --update --no-cache supervisor
COPY docker/supervisord.conf /etc/supervisord.conf

ENV PYTHONPATH=/project/pkgs
COPY src/rejubot/static /project/pkgs/rejubot/static
COPY src/rejubot/templates /project/pkgs/rejubot/templates
COPY --from=builder /project/__pypackages__/3.11/lib /project/pkgs
COPY --from=builder /project/__pypackages__/3.11/bin/* /bin/
WORKDIR /project
EXPOSE 8080/tcp

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]