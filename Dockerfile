FROM python:3.13-slim
WORKDIR /opt/traffic
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt \
    && groupadd --gid 10001 traffic \
    && useradd --uid 10001 --gid traffic --create-home traffic \
    && mkdir -p /opt/traffic/logs /opt/traffic/data /opt/traffic/models \
    && chown -R traffic:traffic /opt/traffic
COPY src src
COPY app.py .
COPY .streamlit .streamlit
USER traffic
EXPOSE 8501 8000
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
