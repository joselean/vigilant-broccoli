FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Ставим зависимости отдельным слоем для кэширования сборки
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && python -c "import tomllib; deps = tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; open('requirements.txt','w').write('\n'.join(deps))" \
    && pip install -r requirements.txt

COPY . .

# По умолчанию — бот; веб-админка переопределяет команду в docker-compose
CMD ["python", "-m", "app.bot.main"]
