FROM python:3.14-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x /app/devops/docker-entrypoint.sh \
    && chmod +x /app/devops/run_app.sh

ENTRYPOINT ["/app/devops/docker-entrypoint.sh"]
CMD ["/app/devops/run_app.sh"]

