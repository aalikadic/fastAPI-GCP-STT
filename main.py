from fastapi import FastAPI
import configparser
import os

config_file = configparser.ConfigParser()
config_file.read('config.ini')

API = str(config_file.get('api','name'))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = API
app = FastAPI()

#domain where this api is hosted for example : localhost:5000/docs to see swagger documentation automagically generated.


@app.get("/")
def home():
    return {"message":"Good to go!"}

@app.post("/GetTranscription")
def get_transcription:
    return {"message":"Transcription Good to go!"}

def initialize_recognition_config():
    
     config_file = configparser.ConfigParser()
     config_file.read('config.ini')
    
     # Initialize the speech recognition
     config = speech.RecognitionConfig()
    
     # Set the configurations
     #config.sample_rate_hertz = int(config_file.get('config','sample_rate'))
     config.language_code = str(config_file.get('config','language_code'))
     config.enable_speaker_diarization = True
     config.encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16  
    # Extract the phrases list from the config.ini
     phrases_list = (config_file.get('speech_context','phrases_list'))
    
     # Set the speech context to match the phrases list from the config.ini
     speech_context = speech.SpeechContext(phrases=phrases_list)
     config.speech_contexts = [speech_context]
    
    
     # Uncomment to get confidences for each word
     #config.enable_word_confidence = True
    
     return config
