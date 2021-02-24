import os
import configparser
import uvicorn
import fleep

import mysql.connector
from mysql.connector.constants import ClientFlag
from google.cloud import storage
from google.cloud import speech_v1p1beta1 as speech
import time
from fastapi import FastAPI, File, HTTPException
#from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

"""DB CONNECTION"""
config = {
    'user': 'root',
    'password': 'infostudio2021',
    'database': 'infostudio_testdb',
    'host': '35.234.96.126',
    'client_flags': [ClientFlag.SSL],
    'ssl_ca': 'ssl/server-ca.pem',
    'ssl_cert': 'ssl/client-cert.pem',
    'ssl_key': 'ssl/client-key.pem'
}

"""FROM THE CONFIGURATION FILE PARSE THE GOOGLE CREDENTIALS"""
config_file = configparser.ConfigParser()
config_file.read('config.ini')

API = str(config_file.get('api','name'))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = API



"""INITIALIZE A FASTAPI INSTANCE"""
app = FastAPI(
    title = "InfoStudio Speech-To-Text API",
    description= "This is the first version of the InfoStudio STT API that utilizes Google Cloud Speech-To-Text API. It accepts audio files with the .wav extension and returns the transcribed audio.",
    #middleware=cors_middleware

    )


"""HEALTH CHECK ENDPOINT, RETURNS A SHORT MESSAGE"""
@app.get("/")
def home():
    return {"message":"Health Check Passed!"}

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)


"""ENDPOINT THAT SHOULD RECEIVE THE FOLLOWING INPUT:
    - single track (mono) WAV file
    - sample rate 48000 Hz (any other sample rate is acceptable also, but best performance is with 48 000)
    - all other extensions (i.e. mp3, m4a) are not acceptable.
   
   THE ENDPOINT RETURNS:
    - transcript: list of transcribed words, every single letter is accessible using its index.
    (i.e.: transcript: barcode potvrda ==> transcript[0] = b, transcript[6] = e);
    - confidence: shows how much the Google Speech-To-Text API is confident that the transcription
    was done properly.
    - transcribed_words: returns a list of every transcribed word, every word is accessible using its index.
    (i.e. transcribed_words = ['lot', 'barcode', 'potvrda', 'lota'] ==> transcribed_words[0] = 'lot').
 """
@app.post("/transcribe",
          responses = {
              404: {"description": "File Not Found"},
              415: {"description": "Unsupported Media Type"},
              200: {"description": "Transcription Successful",
                    "content": {
                        "application/json": {
                            "example": {"transcript":"lot potvrda", "confidence": 0.765, "transcribed_words": ["lot", "potvrda"]},
                            },
                        },
                    },
              })
def get_transcription(audio_file: bytes = File(...)):
    
    if check_if_wav(audio_file):
        audio = speech.RecognitionAudio(content=audio_file)
    
        config = initialize_recognition_config()
    
        transcript, confidence, transcript_words = speech_to_text(config, audio)
        audiofile_name, upload_datetime = upload_file(audio_file)
        insert_transcription_into_db(audiofile_name, transcript, upload_datetime)
        return {"transcript": transcript, "confidence": confidence, "transcribed_words": transcript_words}
    
    else:
        raise HTTPException(status_code=415, detail="Unsupported Media Type")
        
    
    
""" LOADS THE CONFIGURATION FROM THE config.ini FILE. RETURNS A SPEECH RECOGNITION CONFIG FILE 
   THAT CONTAINS INFORMATION ABOUT THE SAMPLE RATE, LANGUAGE CODE, TYPE OF ENCODING, LIST OF 
   WORDS AND PHRASES THAT ARE MORE LIKELY TO OCCUR (i.e. barkod, potvrda, lokacija, vozilo) """
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
    #speech_context = speech.SpeechContext(phrases=phrases_list, boost=20)
    #config.speech_contexts = [speech_context]
    config.metadata = initialize_metadata()
    
    
    
    # Uncomment to get confidences for each word
    #config.enable_word_confidence = True
    
    return config

""" THE ACTUAL TRANSCRIPTION IS DONE HERE. ACCEPTS A CONFIG FILE AND AUDIO THAT IS TO BE TRANSCRIBED. USING THE
    GOOGLE CLOUD SPEECH TO TEXT API GETS THE TRANSCRIBED TEXT ALONG SIDE WITH THE CONFIDENCE """
def speech_to_text(config, audio):
    # Instantiates a client
    client = speech.SpeechClient()
    
    
    response = client.recognize(config=config, audio=audio)
    best_alternative = response.results[0].alternatives[0]
    transcript = best_alternative.transcript
    confidence = best_alternative.confidence
    
    #print_sentences(response)
    
    return transcript, confidence, check_if_comma(return_words(response))

"""INITIALIZES THE METADATA AND ADDS IT TO THE CONFIG FILE"""
def initialize_metadata():
    
    metadata = speech.RecognitionMetadata()
    metadata.interaction_type = speech.RecognitionMetadata.InteractionType.DISCUSSION
    metadata.microphone_distance = (
        speech.RecognitionMetadata.MicrophoneDistance.NEARFIELD
    )
    metadata.recording_device_type = (
    speech.RecognitionMetadata.RecordingDeviceType.SMARTPHONE
    )

    # Some metadata fields are free form strings
    metadata.recording_device_name = "Pixel 2 XL"
    # NAICS code represents the type of industrial place where the
    # recording is going to happen. In our case, the code 452311
    # represents warehouses that deal with general merchandise and food.
    # All the codes can be found at:
    # https://www.naics.com/search/
    metadata.industry_naics_code_of_audio = 452311
    
    return metadata
""" PRINTS OUT THE TRANSCRIPT, CONFIDENCE AND WORD LIST TO THE CONSOLE """
def print_sentences(response):
   
        
    best_alternative = response.results[0].alternatives[0]
        
        
    transcript = best_alternative.transcript.lower()
    confidence = best_alternative.confidence
    print('-' * 60)
    print(f'Transcript: {transcript}')
    print(f'Confidence: {confidence:.0%}')

    print(return_words(response))
   


""" RETURNS ALL THE WORDS FROM THE TRANSCRIPT IN THE FORM OF A LIST WHERE EVERY WORDS CAN BE 
    ACCESSED BY ITS INDEX """
def return_words(response):
    words = []
    best_alternative = response.results[0].alternatives[0]
    
    for i in range(0, len(best_alternative.words)):
        word = best_alternative.words[i].word
        
        #makes the word lowercase
        word = word.lower()
        
        #word = convert_stringnumb_to_float(word)
        #checks if the word is a number
        word = check_if_number(word)
        
        words.append(word)
    
    return words


""" RETURNS ALL THE WORDS AS A SINGLE STRING """  
def return_full_command(response):
    full_command = ''
    best_alternative = response.results[0].alternatives[0]
    
    for i in range(0, len(best_alternative.words)):
        word = best_alternative.words[i].word.lower()
        
        full_command = full_command + ' ' + word
        
    return full_command

  
""" FUNCTION THAT CONVERTS NUMBERS WRITTEN AS STRINGS INTO FLOAT
    (i.e. "12" ==> 12.0). """    
def convert_stringnumb_to_float(number_as_string):
    try: 
        convertedNumber = float(number_as_string)
        
        return convertedNumber
    except:
        
        return number_as_string
"""CHECK IF THE SENT AUDIO FILE IS IN THE CORRECT FORMAT (.wav format)
    IF NOT, SEND BACK AN ERROR"""
def check_if_wav(audio_file):
    wav_str = 'wav'
    audio_info = fleep.get(audio_file)
    #print(audio_info.extension[0])
    if wav_str in audio_info.extension:
        return True
    else:
        return False
"""CHECKS IF THE RESPONSE CONTAINS A COMMA WRITTEN AS A WORD INSTEAD OF SIGN"""

def check_if_comma(words):
    comma_words = ['zarez', 'sars', 'zapeta', 'koma']
    #comma_words = list(config_file.get('commas','comma_list'))
    count = 0
    for word in words:
        
        if word in comma_words:
            words[count] = ','
        count += 1    
    return words

"""CHECKS IF THE WORD IS ACTUALLY A NUMBER WRITTEN USING CHARACTERS. IF YES, CONVERTS THE
    WORD INTO A NUMBER WRITTEN AS STRING (TRI -> 3, NULA -> 0)"""
def check_if_number(word):
    switcher={
        
        'nula': '0',
        'jedan': '1',
        'dva': '2',
        'tri': '3',
        'četiri': '4',
        'pet': '5',
        'šest': '6',
        'sedam': '7',
        'osam': '8',
        'devet': '9'}
    
    try:
        # takes in the word and checks if the given word is the switcher dictionary.
        # if yes, then it changes the word to the corresponding number ("tri"->"3"),
        # if not, then it returns the word unchanged.
        return switcher.get(word, word)
    
    except:
        return word
def upload_file(audio_file):
    """Uploads the audio file to the google cloud storage"""     
    storage_client = storage.Client()
    bucket = storage_client.get_bucket('infostudio-test-bucket')
    
    upload_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
    
    blob_name = "IS" + "_" + upload_datetime
    blob = bucket.blob(blob_name)
     
    blob.upload_from_string(audio_file, content_type="audio/wav")

    return blob_name, upload_datetime  
def insert_transcription_into_db(audiofile_name, transcription, date):
    
    # now we establish our connection
    cnxn = mysql.connector.connect(**config)

    cursor = cnxn.cursor()
    
    query = ("INSERT INTO transcriptions (audiofile_name, transcription, date) "
          "VALUES (%s, %s, %s)")
    values = [audiofile_name,transcription,date]
    cursor.execute(query, values)
    cnxn.commit()  # this commits changes to the database
