from fastapi import FastAPI, File
import configparser
import uvicorn

from google.cloud import speech_v1p1beta1 as speech
import nest_asyncio
nest_asyncio.apply()

config_file = configparser.ConfigParser()
config_file.read('config.ini')


app = FastAPI()

#domain where this api is hosted for example : localhost:5000/docs to see swagger documentation automagically generated.


@app.get("/")
def home():
    return {"message":"Good to go!"}

@app.post("/transcribe")
def get_transcription(audio_file: bytes = File(...)):
    
    client = speech.SpeechClient.from_service_account_json('APIKey.json')
    
    audio = speech.RecognitionAudio(content=audio_file)
    
    config_file = configparser.ConfigParser()
    config_file.read('config.ini')
    
    # Initialize the speech recognition
    config = speech.RecognitionConfig()
    
    config.language_code = str(config_file.get('config','language_code'))
    config.enable_speaker_diarization = True
    config.encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16  
    # Extract the phrases list from the config.ini
    phrases_list = (config_file.get('speech_context','phrases_list'))
    # Set the speech context to match the phrases list from the config.ini
    speech_context = speech.SpeechContext(phrases=phrases_list)
    config.speech_contexts = [speech_context]
    
    
    
    
    response = client.recognize(config=config, audio=audio)
    
    best_alternative = response.results[0].alternatives[0]
    
    transcript = best_alternative.transcript
    
    confidence = best_alternative.confidence
    
    
     
    return {"transcript": transcript, "confidence": confidence}
