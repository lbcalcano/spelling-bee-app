import streamlit as st
import csv
import os
import random
import json
from gtts import gTTS
import tempfile
from datetime import datetime
import base64
import time
import pandas as pd
import sqlite3
import hashlib
import hmac

class SpellingBee:
    def __init__(self):
        self.setup_db()
        self.load_words()
        # Check authentication
        self.check_authentication()
        
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
            
    def check_authentication(self):
        if 'username' not in st.session_state:
            self.show_login()
        
    def show_login(self):
        st.markdown("### 🐝 Spelling Bee Login")  # Smaller login header
        
        # Add guest login button with warning
        st.warning("⚠️ Guest progress will be lost when you close the browser", icon="⚠️")
        if st.button("👤 Continue as Guest", use_container_width=True):
            # Create a unique guest username
            guest_id = f"guest_{int(time.time())}"
            st.session_state.username = guest_id
            st.rerun()
        
        st.write("---")  # Add divider between guest and regular login
        
        # Add tabs for Login and Register
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:  # Login Tab
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_button"):
                if self.verify_credentials(username, password):
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with tab2:  # Register Tab
            new_username = st.text_input("Choose Username", key="reg_username")
            new_password = st.text_input("Choose Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("Register", key="register_button"):
                if self.register_user(new_username, new_password, confirm_password):
                    st.success("Registration successful! Please login.")
                    time.sleep(2)
                    st.rerun()
    
    def register_user(self, username, password, confirm_password):
        try:
            # Basic validation
            if not username or not password:
                st.error("Username and password are required")
                return False
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return False
            
            # Check if username exists
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "users.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Create users table if it doesn't exist
            c.execute('''
                CREATE TABLE IF NOT EXISTS users
                (username TEXT PRIMARY KEY,
                 password_hash TEXT,
                 created_at TEXT)
            ''')
            
            # Check if username exists
            c.execute('SELECT username FROM users WHERE username = ?', (username,))
            if c.fetchone():
                st.error("Username already exists")
                conn.close()
                return False
            
            # Hash the password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Insert new user
            c.execute('''
                INSERT INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
            ''', (username, password_hash, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Registration failed: {str(e)}")
            return False
    
    def verify_credentials(self, username, password):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "users.db")
            
            if not os.path.exists(db_path):
                st.error("No users database found")
                return False
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Get user's password hash
            c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
            result = c.fetchone()
            
            if not result:
                return False
            
            stored_hash = result[0]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            conn.close()
            return stored_hash == password_hash
            
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            return False
    
    def setup_db(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "spelling_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Create progress table
            c.execute('''
                CREATE TABLE IF NOT EXISTS progress
                (user_id TEXT,
                 word TEXT,
                 attempts INTEGER,
                 last_practiced TEXT,
                 PRIMARY KEY (user_id, word))
            ''')
            
            # Create sessions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions
                (user_id TEXT PRIMARY KEY,
                 current_words TEXT,
                 word_count INTEGER,
                 last_updated TEXT)
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Could not setup database: {str(e)}")

    def load_words(self):
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(script_dir, 'spelling_words.csv')
            
            with open(csv_path, 'r') as file:
                reader = csv.reader(file)
                self.words = [row[0].strip().lower() for row in reader]
        except Exception as e:
            st.error(f"Could not load words: {str(e)}")
            self.words = ["example", "test", "words"]  # Default words if file not found
            
    def load_progress(self):
        try:
            if 'username' not in st.session_state:
                return {}
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "spelling_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Get progress for specific user
            c.execute('SELECT word, attempts FROM progress WHERE user_id = ?', 
                     (st.session_state.username,))
            results = c.fetchall()
            
            conn.close()
            
            return {word: attempts for word, attempts in results}
            
        except Exception as e:
            st.error(f"Could not load progress: {str(e)}")
            return {}
            
    def save_progress(self):
        try:
            if 'username' not in st.session_state:
                return
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "spelling_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Update progress for specific user
            for word, attempts in st.session_state.word_stats.items():
                c.execute('''
                    INSERT OR REPLACE INTO progress 
                    (user_id, word, attempts, last_practiced)
                    VALUES (?, ?, ?, ?)
                ''', (st.session_state.username, word, attempts, 
                     datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Could not save progress: {str(e)}")
            
    def speak_word(self, word):
        """Generate speech for the word"""
        try:
            tts = gTTS(text=word, lang='en', slow=False)
            audio_bytes = tempfile.NamedTemporaryFile(suffix='.mp3')
            tts.save(audio_bytes.name)
            
            # Read audio file into bytes and convert to base64
            with open(audio_bytes.name, 'rb') as f:
                audio_bytes_data = f.read()
            
            # Clean up temp file
            audio_bytes.close()
            
            return audio_bytes_data
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            return None

    def save_session(self):
        try:
            if 'username' not in st.session_state or not st.session_state.practice_mode:
                return
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "spelling_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Save current session with debug info
            st.write(f"Saving session: {st.session_state.word_count} words completed")  # Debug info
            
            c.execute('''
                INSERT OR REPLACE INTO sessions
                (user_id, current_words, word_count, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (
                st.session_state.username,
                ','.join(st.session_state.current_words),
                st.session_state.word_count,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Could not save session: {str(e)}")

    def load_session(self):
        try:
            if 'username' not in st.session_state:
                return None
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "spelling_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Get last session
            c.execute('''
                SELECT current_words, word_count, last_updated
                FROM sessions
                WHERE user_id = ?
            ''', (st.session_state.username,))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                words, count, timestamp = result
                return {
                    'words': words.split(','),
                    'count': int(count),  # Ensure count is an integer
                    'timestamp': timestamp
                }
            return None
            
        except Exception as e:
            st.error(f"Could not load session: {str(e)}")
            return None

    def is_admin(self, username):
        return username == "admin"  # You can modify this to include more admin users

    def get_user_stats(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            users_db = os.path.join(script_dir, "users.db")
            progress_db = os.path.join(script_dir, "spelling_progress.db")
            
            users_conn = sqlite3.connect(users_db)
            progress_conn = sqlite3.connect(progress_db)
            
            uc = users_conn.cursor()
            pc = progress_conn.cursor()
            
            # Get registered users
            uc.execute('SELECT username, created_at FROM users')
            registered_users = uc.fetchall()
            
            # Get all users' progress (including guests)
            pc.execute('''
                SELECT user_id, COUNT(DISTINCT word) as words_practiced,
                       COUNT(CASE WHEN attempts = 1 THEN 1 END) as perfect_words,
                       MAX(last_practiced) as last_active
                FROM progress
                GROUP BY user_id
            ''')
            progress_data = pc.fetchall()
            
            # Combine the data
            user_stats = []
            guest_count = 0
            
            for user_id, words, perfect, last_active in progress_data:
                is_guest = user_id.startswith('guest_')
                if is_guest:
                    guest_count += 1
                
                user_stats.append({
                    'Username': user_id,
                    'Type': 'Guest' if is_guest else 'Registered',
                    'Words Practiced': words,
                    'Perfect Words': perfect,
                    'Last Active': datetime.fromisoformat(last_active).strftime('%Y-%m-%d %H:%M')
                })
            
            users_conn.close()
            progress_conn.close()
            
            return {
                'user_stats': user_stats,
                'total_registered': len(registered_users),
                'total_guests': guest_count
            }
            
        except Exception as e:
            st.error(f"Could not get user statistics: {str(e)}")
            return None

def main():
    st.set_page_config(page_title="Spelling Bee Practice", page_icon="🐝")
    
    # Initialize game at the start
    game = SpellingBee()
    
    # Only show title and credit if logged in
    if 'username' in st.session_state:
        st.title("🐝 Spelling Bee Practice")
    
    # Add mobile instructions
    if st.session_state.get('first_visit', True):
        st.info("📱 On mobile devices: Tap 'Play Word' to hear the word. Make sure your sound is on!")
        st.session_state.first_visit = False
    
    if 'username' not in st.session_state:
        return
    
    # Sidebar with statistics
    with st.sidebar:
        st.header("Progress")
        total_words = len(game.words)
        completed = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] <= 2])
        perfect = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] == 1])
        
        st.write(f"📚 Total words: {total_words}")
        st.write(f"✅ Completed: {completed}")
        st.write(f"⭐ Perfect first try: {perfect}")
        
        # Add a divider
        st.write("---")
        
        # Add links to sections
        if st.session_state.word_stats:
            if st.button("📊 View Word Statistics", use_container_width=True):
                st.session_state.show_statistics = True
                st.session_state.practice_mode = False
                st.rerun()
        
        if st.button("Reset Progress"):
            st.session_state.word_stats = {}
            st.session_state.current_word = None
            st.session_state.current_words = []
            st.session_state.attempts = 0
            st.session_state.word_count = 0
            st.session_state.show_statistics = False
            game.save_progress()
            st.rerun()
        
        # Add logout button to sidebar
        st.write(f"Logged in as: {st.session_state.username}")
        if st.button("Logout"):
            del st.session_state.username
            st.rerun()
        
        # Add admin section
        if 'username' in st.session_state and game.is_admin(st.session_state.username):
            st.write("---")
            st.subheader("👑 Admin Dashboard")
            
            stats = game.get_user_stats()
            if stats:
                st.write(f"Total Users: {stats['total_registered'] + stats['total_guests']}")
                st.write(f"- Registered: {stats['total_registered']}")
                st.write(f"- Guests: {stats['total_guests']}")
                
                st.write("---")
                st.write("User Details:")
                
                # Create DataFrame for user stats
                df = pd.DataFrame(stats['user_stats'])
                
                # Sort by Perfect Words (descending)
                df = df.sort_values('Perfect Words', ascending=False)
                
                # Display the DataFrame
                st.dataframe(
                    df,
                    column_config={
                        "Username": st.column_config.TextColumn("User", width=150),
                        "Type": st.column_config.TextColumn("Type", width=100),
                        "Words Practiced": st.column_config.NumberColumn("Words", width=80),
                        "Perfect Words": st.column_config.NumberColumn("Perfect", width=80),
                        "Last Active": st.column_config.TextColumn("Last Active", width=150)
                    },
                    hide_index=True
                )
    
    # Main practice area
    if 'practice_mode' not in st.session_state:
        st.session_state.practice_mode = False
    if 'show_statistics' not in st.session_state:
        st.session_state.show_statistics = False
    
    if st.session_state.show_statistics:
        st.header("📊 Word Statistics Report")
        if st.button("← Back to Practice", type="secondary"):
            st.session_state.show_statistics = False
            st.rerun()
            
        # Show detailed results
        if st.session_state.word_stats:
            # Create a list of dictionaries for the DataFrame
            word_stats_data = []
            for word, attempts in st.session_state.word_stats.items():
                if attempts == 1:
                    status = "⭐"
                    result = "Perfect!"
                elif attempts == 2:
                    status = "✅"
                    result = "Learned"
                else:
                    status = "📝"
                    result = "Needs Practice"
                
                word_stats_data.append({
                    "Word": word,
                    "Status": status,
                    "Attempts": attempts,
                    "Result": result
                })
            
            # Sort by attempts (descending)
            word_stats_data.sort(key=lambda x: x["Attempts"], reverse=True)
            
            # Create and display DataFrame
            df = pd.DataFrame(word_stats_data)
            st.dataframe(
                df,
                column_config={
                    "Word": st.column_config.TextColumn("Word", width=200),
                    "Status": st.column_config.TextColumn("Status", width=100),
                    "Attempts": st.column_config.NumberColumn("Attempts", width=100),
                    "Result": st.column_config.TextColumn("Result", width=150)
                },
                hide_index=True
            )
            
            # Add summary statistics
            st.write("---")
            st.write("Summary:")
            perfect = len([d for d in word_stats_data if d["Attempts"] == 1])
            learned = len([d for d in word_stats_data if d["Attempts"] == 2])
            practice = len([d for d in word_stats_data if d["Attempts"] > 2])
            
            st.write(f"⭐ Perfect first try: {perfect}")
            st.write(f"✅ Learned after retry: {learned}")
            st.write(f"📝 Need more practice: {practice}")
    
    elif not st.session_state.practice_mode:
        # Check for existing session
        last_session = game.load_session()
        
        # Add practice buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Start New Practice"):
                available_words = [w for w in game.words if w not in st.session_state.word_stats]
                st.session_state.current_words = random.sample(
                    available_words,
                    len(available_words)
                )
                st.session_state.practice_mode = True
                st.session_state.word_count = 0
                game.save_session()
                st.rerun()
        
        with col2:
            if last_session:
                last_time = datetime.fromisoformat(last_session['timestamp'])
                time_diff = datetime.now() - last_time
                if time_diff.days == 0:
                    time_ago = "today"
                elif time_diff.days == 1:
                    time_ago = "yesterday"
                else:
                    time_ago = f"{time_diff.days} days ago"
                
                # Show remaining words instead of total
                current_word_index = last_session['count']
                remaining_words = len(last_session['words']) - current_word_index
                progress = f"{remaining_words} words remaining"
                
                if st.button(f"Continue Last Practice ({progress}, {time_ago})"):
                    st.session_state.current_words = last_session['words']
                    st.session_state.word_count = current_word_index  # Use the exact index
                    st.session_state.practice_mode = True
                    st.session_state.current_word = None
                    st.session_state.attempts = 0
                    st.rerun()
        
        with col3:
            if st.button("Practice Wrong Words"):
                wrong_words = [w for w in game.words if w in st.session_state.word_stats 
                             and st.session_state.word_stats[w] > 1]
                if wrong_words:
                    st.session_state.current_words = random.sample(
                        wrong_words,
                        len(wrong_words)
                    )
                    st.session_state.practice_mode = True
                    st.session_state.word_count = 0
                    game.save_session()
                    st.rerun()
                else:
                    st.warning("No words to practice!")
    
    else:  # Practice mode
        if not st.session_state.current_words:
            st.session_state.practice_mode = False
            st.rerun()
            
        # Add mobile warning at start of practice
        st.warning("""
            📱 Important for Mobile Users:
            1. Turn OFF your keyboard auto-correction
            2. Type exactly as you hear
            3. Check your spelling before submitting
        """)
        
        # Initialize new word and play audio
        if st.session_state.current_word is None:
            st.session_state.current_word = st.session_state.current_words[st.session_state.word_count]
            st.session_state.attempts = 0
            # Generate audio
            audio_data = game.speak_word(st.session_state.current_word)
            st.session_state.current_audio = audio_data
            
        # Display progress
        total_practice_words = len(st.session_state.current_words)
        remaining_words = total_practice_words - st.session_state.word_count
        st.write(f"Word {st.session_state.word_count + 1} of {total_practice_words} ({remaining_words} remaining)")
        
        # Audio controls in a more mobile-friendly way
        st.write("👇 Tap the play button below to hear the word:")
        
        # Create two columns for better layout
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("### 🔊")
        with col2:
            if st.session_state.current_audio is not None:
                # Create HTML with audio element
                audio_html = f'''
                    <audio controls>
                        <source src="data:audio/mpeg;base64,{base64.b64encode(st.session_state.current_audio).decode()}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                    '''
                st.components.v1.html(audio_html, height=50)
        
        # Add a spacer
        st.write("")
        
        # Generate unique keys for form and input
        form_key = f"word_form_{st.session_state.word_count}_{st.session_state.attempts}"
        input_key = f"word_input_{st.session_state.word_count}_{st.session_state.attempts}"
        
        # Word input form
        with st.form(key=form_key):
            # Add custom HTML to disable autocorrect and autocapitalize
            st.markdown("""
                <style>
                /* Disable iOS text input features */
                input[type="text"] {
                    -webkit-text-security: none !important;
                    -webkit-appearance: none !important;
                    -moz-appearance: none !important;
                    appearance: none !important;
                    autocorrect: off !important;
                    -webkit-autocorrect: off !important;
                    -webkit-autocapitalize: none !important;
                    autocapitalize: none !important;
                    spellcheck: false !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            user_input = st.text_input(
                "Type the word and press Enter:", 
                key=input_key,
                value="",
                autocomplete="off",  # Disable browser autocomplete
                help="Type exactly as shown - turn off your keyboard auto-correction!"  # Add helpful tooltip
            ).strip().lower()
            submit_button = st.form_submit_button("Submit")
            
            if submit_button:
                if user_input == st.session_state.current_word:
                    success_container = st.empty()
                    success_container.success("✨ Correct! Moving to next word in 2 seconds...")
                    st.session_state.word_stats[st.session_state.current_word] = st.session_state.attempts + 1
                    game.save_progress()
                    time.sleep(2)
                    st.session_state.word_count += 1
                    st.session_state.current_word = None
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts == 1:
                        st.error("❌ Incorrect. Try once more!")
                        st.write("Listen again:")
                        time.sleep(1)
                        st.rerun()
                    else:
                        error_container = st.empty()
                        error_container.error(f"❌ Incorrect. The correct spelling is: {st.session_state.current_word}")
                        st.session_state.word_stats[st.session_state.current_word] = st.session_state.attempts
                        game.save_progress()
                        time.sleep(3)
                        st.session_state.word_count += 1
                        st.session_state.current_word = None
                        st.rerun()
        
        if st.button("Quit Practice"):
            game.save_session()  # Save session before quitting
            st.session_state.practice_mode = False
            st.session_state.current_word = None
            st.session_state.current_words = []
            st.rerun()

    # Keep only the bottom credit
    st.markdown("<br><hr><div style='text-align: center; color: gray; font-size: 0.8em; padding: 20px;'>Developed by LBC Productions</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main() 