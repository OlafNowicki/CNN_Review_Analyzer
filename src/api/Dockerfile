FROM python:3.8

ADD requirements.txt /app/
WORKDIR /app

RUN pip3 install -vvv --no-cache-dir -r requirements.txt
RUN pip3 install torch===1.7.1 torchvision===0.8.2 torchaudio===0.7.2 -f https://download.pytorch.org/whl/torch_stable.html

ADD . /app

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
