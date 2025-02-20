import streamlit as st
import csv
import os
import random
import json
from gtts import gTTS
import tempfile
from datetime import datetime
import base64

class SpellingBee:
    def __init__(self):
        self.load_words()
        # Initialize session state if not exists
        if 'word_stats' not in st.session_state:
            st.session_state.word_stats = self.load_progress()
        if 'current_word' not in st.session_state:
            st.session_state.current_word = None
        if 'current_words' not in st.session_state:
            st.session_state.current_words = []
        if 'attempts' not in st.session_state:
            st.session_state.attempts = 0
        if 'word_count' not in st.session_state:
            st.session_state.word_count = 0
            
    def load_words(self):
        try:
            with open('spelling_words.csv', 'r') as file:
                reader = csv.reader(file)
                self.words = [row[0].strip().lower() for row in reader]
        except:
            self.words = ["example", "test", "words"]  # Default words if file not found
            
    def load_progress(self):
        try:
            with open("spelling_progress.json", 'r') as f:
                return json.load(f)
        except:
            return {}
            
    def save_progress(self):
        with open("spelling_progress.json", 'w') as f:
            json.dump(st.session_state.word_stats, f)
            
    def speak_word(self, word):
        """Generate speech for the word and return audio HTML"""
        tts = gTTS(text=word, lang='en')
        # Save audio to a bytes buffer
        audio_bytes = tempfile.NamedTemporaryFile()
        tts.save(audio_bytes.name)
        
        # Auto-play audio using HTML
        with open(audio_bytes.name, 'rb') as f:
            audio_data = f.read()
        audio_bytes.close()
        
        audio_base64 = base64.b64encode(audio_data).decode()
        audio_html = f'<audio autoplay><source src="data:audio/mp3;base64,{audio_base64}"></audio>'
        st.components.v1.html(audio_html, height=0)
        
        # Also return the base64 data for the repeat button
        return audio_base64

def main():
    st.set_page_config(page_title="Spelling Bee Practice", page_icon="🐝")
    
    st.title("🐝 Spelling Bee Practice")
    
    game = SpellingBee()
    
    # Sidebar with statistics
    with st.sidebar:
        st.header("Progress")
        total_words = len(game.words)
        completed = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] <= 2])
        perfect = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] == 1])
        
        st.write(f"📚 Total words: {total_words}")
        st.write(f"✅ Completed: {completed}")
        st.write(f"⭐ Perfect first try: {perfect}")
        
        if st.button("Reset Progress"):
            st.session_state.word_stats = {}
            st.session_state.current_word = None
            st.session_state.current_words = []
            st.session_state.attempts = 0
            st.session_state.word_count = 0
            game.save_progress()
            st.rerun()
    
    # Main practice area
    if 'practice_mode' not in st.session_state:
        st.session_state.practice_mode = False
    
    if not st.session_state.practice_mode:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start New Practice"):
                st.session_state.current_words = random.sample(
                    [w for w in game.words if w not in st.session_state.word_stats],
                    min(10, len([w for w in game.words if w not in st.session_state.word_stats]))
                )
                st.session_state.practice_mode = True
                st.session_state.word_count = 0
                st.rerun()
        
        with col2:
            if st.button("Practice Wrong Words"):
                wrong_words = [w for w in game.words if w in st.session_state.word_stats 
                             and st.session_state.word_stats[w] > 1]
                if wrong_words:
                    st.session_state.current_words = random.sample(wrong_words, min(10, len(wrong_words)))
                    st.session_state.practice_mode = True
                    st.session_state.word_count = 0
                    st.rerun()
                else:
                    st.warning("No words to practice!")
        
        # Show results
        if st.session_state.word_stats:
            st.header("Results")
            for word, attempts in st.session_state.word_stats.items():
                status = "⭐" if attempts == 1 else "✅" if attempts == 2 else "📝"
                st.write(f"{status} {word}: {attempts} attempt(s)")
    
    else:  # Practice mode
        if not st.session_state.current_words:
            st.session_state.practice_mode = False
            st.rerun()
            
        # Initialize new word and play audio
        if st.session_state.current_word is None:
            st.session_state.current_word = st.session_state.current_words[st.session_state.word_count]
            st.session_state.attempts = 0
            # Generate and play audio
            audio_base64 = game.speak_word(st.session_state.current_word)
            st.session_state.current_audio = audio_base64
            
        # Display progress
        st.write(f"Word {st.session_state.word_count + 1} of {len(st.session_state.current_words)}")
        
        # Audio controls for repeat
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔊 Repeat"):
                audio_html = f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state.current_audio}"></audio>'
                st.components.v1.html(audio_html, height=0)
        
        # Generate unique keys for form and input
        form_key = f"word_form_{st.session_state.word_count}_{st.session_state.attempts}"
        input_key = f"word_input_{st.session_state.word_count}_{st.session_state.attempts}"
        
        # Word input using a form with unique keys
        with st.form(key=form_key):
            user_input = st.text_input("Type the word and press Enter:", 
                                     key=input_key,
                                     value="").strip().lower()
            submit_button = st.form_submit_button("Submit")
            
            if submit_button:
                if user_input == st.session_state.current_word:
                    st.success("✨ Correct!")
                    st.session_state.word_stats[st.session_state.current_word] = st.session_state.attempts + 1
                    game.save_progress()
                    
                    # Move to next word
                    st.session_state.word_count += 1
                    st.session_state.current_word = None
                    st.rerun()
                    
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts == 1:
                        st.error("❌ Incorrect. Try once more!")
                        # Speak the word again after first wrong attempt
                        os.system(f'say "{st.session_state.current_word}"')
                        st.rerun()
                    else:
                        st.error(f"❌ Incorrect. The correct spelling is: {st.session_state.current_word}")
                        st.session_state.word_stats[st.session_state.current_word] = st.session_state.attempts
                        game.save_progress()
                        
                        # Move to next word
                        st.session_state.word_count += 1
                        st.session_state.current_word = None
                        st.rerun()
        
        if st.button("Quit Practice"):
            st.session_state.practice_mode = False
            st.session_state.current_word = None
            st.session_state.current_words = []
            st.rerun()

if __name__ == "__main__":
    main() 