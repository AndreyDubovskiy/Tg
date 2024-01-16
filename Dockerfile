FROM python:alpine3.9
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip
RUN pip install --upgrade pip setuptools
RUN apk add gcc musl-dev linux-headers python3-dev
RUN pip install -r requirements.txt
CMD ["python", "main.py"]