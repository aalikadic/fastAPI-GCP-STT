from fastapi import FastAPI
import configparser

config_file = configparser.ConfigParser()
config_file.read('config.ini')
app = FastAPI()

#domain where this api is hosted for example : localhost:5000/docs to see swagger documentation automagically generated.


@app.get("/")
def home():
    return {"message":"Good to go!"}
