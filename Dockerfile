FROM python:3.8
RUN mkdir /app
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install pip wheel --upgrade && pip install -r requirements.txt --no-color
COPY download-api-raml.sh download-api-raml.sh
RUN ./download-api-raml.sh
RUN touch client-secrets.json
COPY . .
CMD ["./manage.sh", "runserver", "0.0.0.0:8000"]
