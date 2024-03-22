import streamlit as st
import streamlit_authenticator as stauth
from pytube import YouTube
import os
import sys
from time import sleep
import requests
from zipfile import ZipFile
import yaml
from yaml.loader import SafeLoader

#################
# APP LOGIC
################

st.title("Speech to Text App")
bar = st.progress(0)


def get_yt(url):
    """ Function that downloads YouTube video from the specified URL. """
    video = YouTube(url)
    yt = video.streams.get_audio_only()
    yt_file = yt.download()
    bar.progress(10)


def upload_file(uploaded_file):
    """ Function that allows users to upload a file for transcription. """
    os.getcwd()
    with open(os.path.join(os.getcwd(), uploaded_file.name), "wb") as f:
        f.write(uploaded_file.getbuffer())
        # file_details = {"FileName":uploaded_file .name,"FileType":uploaded_file .type}
        # st.write(str(f))

    st.info("Audio file has been uploaded.")
    bar.progress(10)


def transcribe_audio_file():
    """ Function that sends file to AssemblyAI and starts the transcription process. """
    current_dir = os.getcwd()
    mp4_file = None
    filename = None
    for file in os.listdir(current_dir):
        if file.endswith((".mp4", ".mp3", ".m4a", ".wav")):
            mp4_file = os.path.join(current_dir, file)
    filename = mp4_file
    st.info("Audio file has been transferred to Assembly AI.")
    bar.progress(20)

    def read_file(filename, chunk_size=5242880):
        """ Function that reads uploaded file and checks the chunk size."""
        with open(filename, "rb") as _file:
            while True:
                data = _file.read(chunk_size)
                if not data:
                    break
                yield data
    headers = {"authorization": api_key}
    response = requests.post("https://api.assemblyai.com/v2/upload",
                             headers=headers,
                             data=read_file(filename),
                             )
    audio_url = response.json()["upload_url"]
    bar.progress(30)

    endpoint = "https://api.assemblyai.com/v2/transcript"
    json = {"audio_url": audio_url, "language_code": "pl"}
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }
    transcript_input_response = requests.post(endpoint, json=json, headers=headers)
    bar.progress(40)

    transcript_id = transcript_input_response.json()["id"]
    bar.progress(50)

    endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    headers = {"authorization": api_key}
    transcript_output_response = requests.get(endpoint, headers=headers)
    bar.progress(60)
    st.warning("Transcription is processing...")

    # Checking if transcription is complete.

    while transcript_output_response.json()["status"] != "completed":
        sleep(5)
        transcript_output_response = requests.get(endpoint, headers=headers)
    bar.progress(100)
    st.warning("Transcription is processed.")
    st.balloons()

    # Printing transcribed text.
    st.header("Output: ")
    st.success(transcript_output_response.json()["text"])

    # Saving as a TXT file.
    txt = open("transcription.txt", 'w')
    txt.write(transcript_output_response.json()["text"])
    txt.close()

    # Saving as DOC file.
    txt = open("transcription.doc", 'w')
    txt.write(transcript_output_response.json()["text"])
    txt.close()

    # Making ZIP package.
    zip_file = ZipFile('transcription.zip', 'w')
    zip_file.write('transcription.txt')
    zip_file.write('transcription.doc')
    zip_file.close()
    # Removing the file.
    os.remove(filename)


########
# APP CONSTRUCTION
########

# User authentication:
with open('config.YAML') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('main')

if authentication_status:
    authenticator.logout('Logout', 'main')
    st.write(f'Welcome *{name}*')
    # Extracting the API_text from .env.
    api_key = st.secrets["API_KEY"]

    st.sidebar.header("Input parameter")
    with st.sidebar.form(key="my_form"):
        url = st.text_input("Enter URL of YouTube video:")
        uploaded_file = st.file_uploader("Upload your audio file:", type=["mp4", "wav", "m4a", "mp3"])
        submit_button = st.form_submit_button(label="Transcribe")
    # When user does not upload a file
    if (uploaded_file is None) and (str(url) == ''):
        st.warning("Awaiting URL input or uploaded audio file in the sidebar for transcription.")

    # When user clicks a button:
    if submit_button:
        # If user uploads a file and url is not empty:
        if (str(url) != '') and (uploaded_file is not None):
            st.sidebar.warning('Only one option is possible!')
            raise Exception("You must provide a URL or an audio file, not both!")
        # When user uploads a file:
        elif uploaded_file is not None:
            upload_file(uploaded_file)
            transcribe_audio_file()
        # When user provides URL to a YouTube video:
        elif str(url) != '':
            get_yt(url)
            transcribe_audio_file()
        # When user does not provide URL and does not upload a file:
        else:
            st.sidebar.warning('Please provide URL input or uploaded audio file! ')
            raise Exception("You must provide a URL or an audio file!")

        with open("transcription.zip", "rb") as zip_download:
            st.download_button(
                label="Download ZIP",
                data=zip_download,
                file_name="transcription.zip",
                mime="application/zip"
            )
elif authentication_status is False:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')