from fastapi import FastAPI, File
import configparser
import os
from google.cloud import speech_v1p1beta1 as speech

config_file = configparser.ConfigParser()
config_file.read('config.ini')

API = str(config_file.get('api','name'))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = API
app = FastAPI()

#domain where this api is hosted for example : localhost:5000/docs to see swagger documentation automagically generated.


@app.get("/")
def home():
    return {"message":"Good to go!"}

@app.post("/transcribe")
#def get_transcription():
    #return {"message":"Transcription Good to go!"}

def get_transcription(audio_file: bytes = File(...)):
    return {"message":"Transcription Good to go!"}

