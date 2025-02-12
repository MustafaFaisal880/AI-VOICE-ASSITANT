import os
import pygame
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
import speech_recognition as sr
import threading

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_APIKEY")
client = OpenAI(api_key=api_key)

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# Flag to control audio interruption
stop_audio_flag = threading.Event()

# Function to play audio with interrupt support
def play_audio(audio_binary):
    global stop_audio_flag
    stop_audio_flag.clear()  # Reset the stop flag

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        temp_audio.write(audio_binary)
        temp_audio.flush()
    
    pygame.mixer.music.load(temp_audio.name)
    pygame.mixer.music.play()

    # Wait for either playback to finish or the stop flag to be set
    while pygame.mixer.music.get_busy():
        if stop_audio_flag.is_set():
            pygame.mixer.music.stop()
            print("Playback interrupted.")
            break

# Function to listen for continuous voice input and detect interruptions
def listen_continuously():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("Adjusting microphone for ambient noise... Please wait.")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Ready! Start speaking... Say 'exit' to quit.")

    while True:
        try:
            with mic as source:
                print("Listening...")
                
                # Start listening in a non-blocking way
                audio = recognizer.listen(source, phrase_time_limit=10)
                print("Processing speech...")
                
                # Interrupt playback if any sound is detected
                if pygame.mixer.music.get_busy():
                    stop_audio_flag.set()

                # Recognize speech
                user_input = recognizer.recognize_google(audio)
                print(f"You said: {user_input}")

                # Check for exit command
                if user_input.lower() in ["exit", "quit"]:
                    print("Exiting conversation...")
                    break

                # Step 1: Generate AI response using GPT-4
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "developer",
                         "content": "You are a helpful assistant."},
                        
                        {"role": "user",
                         "content": user_input}
                    ]
                )
                ai_reply = response.choices[0].message.content.strip()
                print("AI Reply:", ai_reply)

                # Step 2: Generate AI speech from text
                tts_response = client.audio.speech.create(
                    model="tts-1",
                    voice="ash",
                    input=ai_reply
                )

                # Step 3: Play AI-generated speech (interruptible)
                audio_thread = threading.Thread(target=play_audio, args=(tts_response.read(),))
                audio_thread.start()

        except sr.UnknownValueError:
            print("Could not understand your speech. Please try again.")
        except sr.RequestError as e:
            print(f"Error with speech recognition: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    pygame.mixer.quit()


# Start the listening loop
if __name__ == "__main__":
    listen_continuously()

