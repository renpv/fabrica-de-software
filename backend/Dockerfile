# Back-end da Fábrica: Django + DRF atrás do gunicorn. Contexto de build: backend/.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependências primeiro, para aproveitar o cache de camadas.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# collectstatic só precisa que o settings carregue; estes valores valem apenas neste passo
# e não ficam na imagem (o ambiente real vem do compose).
RUN DATABASE_URL=postgres://x:x@localhost/x DJANGO_SECRET_KEY=so-para-collectstatic \
    FABRICA_URL_PUBLICA=http://localhost \
    FABRICA_CHAVES_COFRE=wE4d6T-2qefhzG4CJH6IH9zc6fx0Bo4LzxoW3Pn9V4I= \
    DJANGO_STATIC_ROOT=/app/staticfiles python manage.py collectstatic --noinput \
    && useradd --system --no-create-home --uid 10001 fabrica

USER fabrica
ENV DJANGO_STATIC_ROOT=/app/staticfiles
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
