import base64
import html
import io
import json
import math
import random
import re
import secrets
import string
import struct
import wave
from pathlib import Path
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components
from filelock import FileLock
from streamlit_local_storage import LocalStorage


# Poker high-card ordering for ranks and suits.
# Bigger numbers mean stronger cards.
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["Clubs", "Diamonds", "Hearts", "Spades"]

RANK_STRENGTH = {rank: index for index, rank in enumerate(RANKS)}
SUIT_STRENGTH = {suit: index for index, suit in enumerate(SUITS)}

SUIT_SYMBOLS = {
    "Spades": "♠",
    "Hearts": "♥",
    "Diamonds": "♦",
    "Clubs": "♣",
}

AUTO_JUDGE_MODE = "Auto judge"
TABLE_MODE = "Table mode"
PRIVATE_DEVICE_MODE = "Private device mode"
PLAY_MODES = [PRIVATE_DEVICE_MODE, TABLE_MODE, AUTO_JUDGE_MODE]

TABLES_FILE = Path("private_tables.json")
TABLES_TEMP_FILE = Path("private_tables.tmp")
TABLES_LOCK = FileLock("private_tables.lock", timeout=5)
TITLE_IMAGE = Path("assets/poker-title.png")
CARD_ASSETS_DIR = Path("assets/cards")
CARD_RANK_NAMES = {
    "A": "ace",
    "J": "jack",
    "Q": "queen",
    "K": "king",
}
LIVE_APP_URL = "https://poker-high-card.streamlit.app/"
LINKEDIN_SHARE_URL = (
    "https://www.linkedin.com/sharing/share-offsite/?url="
    + quote(LIVE_APP_URL, safe="")
)
NICKNAME_STORAGE_KEY = "poker_high_card_nickname"


def create_deck():
    """Create a standard 52-card deck."""
    deck = []

    for suit in SUITS:
        for rank in RANKS:
            deck.append({"rank": rank, "suit": suit})

    return deck


def card_strength(card):
    """Return a card's strength as rank first, then suit for ties."""
    return (RANK_STRENGTH[card["rank"]], SUIT_STRENGTH[card["suit"]])


def strength_label(card):
    """Explain the strength that is used to compare this card."""
    rank_points = RANK_STRENGTH[card["rank"]] + 1
    suit_points = SUIT_STRENGTH[card["suit"]] + 1
    return f"Rank strength {rank_points}, suit strength {suit_points}"


def format_card(card):
    """Create a friendly card label for display."""
    symbol = SUIT_SYMBOLS[card["suit"]]
    return f"{card['rank']} {symbol} {card['suit']}"


def draw_cards(player_names):
    """Shuffle the deck and draw one unique card for each player."""
    deck = create_deck()
    random.shuffle(deck)

    results = []
    for player_name in player_names:
        results.append(
            {
                "player": player_name,
                "card": deck.pop(),
            }
        )

    return results


def draw_cards_for_players(players):
    """Shuffle one deck and attach one unique card to each saved player."""
    deck = create_deck()
    random.shuffle(deck)

    for player in players:
        player["card"] = deck.pop()

    return players


def find_winner(results):
    """Find the player with the strongest high card."""
    return max(results, key=lambda result: card_strength(result["card"]))


def sort_results_by_strength(results):
    """Show strongest cards first in the ranking table."""
    return sorted(results, key=lambda result: card_strength(result["card"]), reverse=True)


def reset_draw():
    """Clear the current draw and return the app to its starting state."""
    st.session_state.pop("results", None)
    st.session_state.pop("draw_id", None)


def preferred_nickname(default="Player"):
    """Return the remembered nickname or a friendly fallback."""
    return st.session_state.get("nickname", "").strip() or default


def nickname_changed():
    """Require a fresh save when the nickname text is edited."""
    st.session_state.nickname_saved = False


def remember_nickname(local_storage):
    """Save the nickname in this browser for future visits."""
    nickname = preferred_nickname()
    st.session_state.nickname_saved = True

    st.session_state.host_name = nickname
    st.session_state.join_name = nickname
    st.session_state.player_name_1 = nickname

    local_storage.setItem(
        NICKNAME_STORAGE_KEY,
        nickname,
        key="save_poker_nickname",
    )


def enter_play_mode(mode):
    """Continue directly to the selected mode after the nickname is saved."""
    st.session_state.play_style = mode
    st.session_state.title_screen_complete = True
    st.rerun()


def load_private_tables():
    """Load private tables from a small local JSON file."""
    with TABLES_LOCK:
        if not TABLES_FILE.exists():
            return {}

        with TABLES_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)


def save_private_tables(tables):
    """Save private tables so different browsers can share the same table."""
    with TABLES_LOCK:
        # Write a complete temporary file first, then replace the old file at once.
        # This prevents another browser from reading a half-written table file.
        with TABLES_TEMP_FILE.open("w", encoding="utf-8") as file:
            json.dump(tables, file, indent=2)

        TABLES_TEMP_FILE.replace(TABLES_FILE)


def clean_table_code(table_code):
    """Normalize a pasted table code and ignore spaces or punctuation."""
    return re.sub(r"[^A-Z0-9]", "", table_code.upper())


def make_table_code():
    """Create a short table code that is easy to read aloud."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def create_private_table(number_of_players, host_name):
    """Create a new private table and add the host as the first player."""
    with TABLES_LOCK:
        tables = load_private_tables()
        table_code = make_table_code()

        while table_code in tables:
            table_code = make_table_code()

        player_id = st.session_state.private_player_id
        tables[table_code] = {
            "host_id": player_id,
            "number_of_players": number_of_players,
            "status": "waiting",
            "players": [
                {
                    "id": player_id,
                    "name": host_name,
                    "card": None,
                }
            ],
        }

        save_private_tables(tables)

    st.session_state.private_table_code = table_code
    st.query_params["table"] = table_code


def join_private_table(table_code, player_name):
    """Join an existing private table from a different browser session."""
    table_code = clean_table_code(table_code)
    if not table_code:
        return "Enter a table code."

    with TABLES_LOCK:
        tables = load_private_tables()
        table = tables.get(table_code)

        if table is None:
            return "That table code was not found. Check the code with the host and try again."

        if table["status"] == "dealt":
            return "Cards have already been dealt for that table."

        player_id = st.session_state.private_player_id
        for player in table["players"]:
            if player["id"] == player_id:
                player["name"] = player_name
                save_private_tables(tables)
                break
        else:
            if len(table["players"]) >= table["number_of_players"]:
                return "That table is already full."

            table["players"].append({"id": player_id, "name": player_name, "card": None})
            save_private_tables(tables)

    st.session_state.private_table_code = table_code
    st.query_params["table"] = table_code
    return None


def deal_private_table(table_code):
    """Deal one card to every player in a private table."""
    with TABLES_LOCK:
        tables = load_private_tables()
        table = tables.get(table_code)

        if table is None:
            return

        table["players"] = draw_cards_for_players(table["players"])
        table["status"] = "dealt"
        table["draw_id"] = secrets.token_hex(6)
        save_private_tables(tables)


def redeal_private_table(table_code):
    """Deal a fresh round to the same private table players."""
    deal_private_table(table_code)


def leave_private_table():
    """Forget the table on this browser without deleting it for others."""
    st.session_state.pop("private_table_code", None)
    st.query_params.clear()


@st.cache_data
def title_image_data():
    """Read the title artwork once and turn it into an embeddable image."""
    return base64.b64encode(TITLE_IMAGE.read_bytes()).decode("ascii")


def synthesize_music(events):
    """Turn a short list of notes into an original WAV track."""
    sample_rate = 16000
    samples = []

    for frequencies, duration, volume in events:
        sample_count = int(sample_rate * duration)
        for index in range(sample_count):
            time_position = index / sample_rate
            fade_in = min(1.0, index / (sample_rate * 0.025))
            fade_out = min(1.0, (sample_count - index) / (sample_rate * 0.08))
            envelope = fade_in * fade_out

            # A quiet second harmonic makes the generated sine waves feel warmer.
            tone = sum(
                math.sin(2 * math.pi * frequency * time_position)
                + 0.18 * math.sin(4 * math.pi * frequency * time_position)
                for frequency in frequencies
            ) / len(frequencies)
            samples.append(int(32767 * volume * envelope * tone))

    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))

    return audio.getvalue()


@st.cache_data
def title_music_audio():
    """Create a relaxed card-room theme for the title screen."""
    chords = [
        [130.81, 261.63, 329.63, 392.00],
        [110.00, 220.00, 261.63, 329.63],
        [146.83, 293.66, 349.23, 440.00],
        [98.00, 196.00, 246.94, 349.23],
    ]
    melody = [
        659.25, 783.99, 659.25, 587.33,
        523.25, 659.25, 523.25, 493.88,
        587.33, 698.46, 587.33, 523.25,
        493.88, 587.33, 523.25, 392.00,
    ]
    events = []

    for index, melody_note in enumerate(melody):
        chord = chords[(index // 4) % len(chords)]
        events.append((chord + [melody_note], 0.48, 0.20))

    return synthesize_music(events)


@st.cache_data
def gameplay_music_audio():
    """Create a low-key suspense theme for choosing and drawing cards."""
    chords = [
        [110.00, 220.00, 261.63, 329.63],
        [87.31, 174.61, 220.00, 261.63],
        [73.42, 146.83, 174.61, 220.00],
        [82.41, 164.81, 207.65, 246.94],
    ]
    melody = [
        440.00, 523.25, 493.88, 440.00,
        349.23, 440.00, 392.00, 349.23,
        293.66, 349.23, 329.63, 293.66,
        329.63, 415.30, 392.00, 329.63,
    ]
    events = []

    for index, melody_note in enumerate(melody):
        chord = chords[(index // 4) % len(chords)]
        events.append((chord + [melody_note], 0.52, 0.16))

    return synthesize_music(events)


@st.cache_data
def result_music_audio():
    """Create a bright result fanfare that resolves into the gameplay theme."""
    events = [
        ([261.63, 523.25, 659.25], 0.24, 0.25),
        ([329.63, 659.25, 783.99], 0.24, 0.25),
        ([392.00, 783.99, 987.77], 0.28, 0.27),
        ([523.25, 659.25, 783.99, 1046.50], 0.72, 0.25),
    ]
    return synthesize_music(events)


def render_music(audio_bytes, loop=True, fallback_audio=None):
    """Play one hidden track, optionally returning to gameplay music afterward."""
    audio_data = base64.b64encode(audio_bytes).decode("ascii")
    fallback_data = (
        base64.b64encode(fallback_audio).decode("ascii")
        if fallback_audio
        else ""
    )
    loop_attribute = "loop" if loop else ""

    # The audio lives in a tiny component so the page stays focused on the game.
    components.html(
        f"""
        <audio id="poker-music" src="data:audio/wav;base64,{audio_data}"
            {loop_attribute} autoplay></audio>
        <script>
            const player = document.getElementById("poker-music");
            const fallback = "{fallback_data}";
            player.volume = 0.22;
            player.play().catch(() => {{}});

            if (fallback) {{
                player.addEventListener("ended", () => {{
                    player.src = "data:audio/wav;base64," + fallback;
                    player.loop = true;
                    player.volume = 0.18;
                    player.play().catch(() => {{}});
                }}, {{ once: true }});
            }}
        </script>
        """,
        height=1,
    )


def play_scene_music(scene, result_token=None):
    """Choose the right music for the current part of the experience."""
    if not st.session_state.get("music_enabled", False):
        return

    if scene == "title":
        render_music(title_music_audio())
        return

    if scene == "result" and result_token:
        if st.session_state.get("last_result_music_token") != result_token:
            render_music(
                result_music_audio(),
                loop=False,
                fallback_audio=gameplay_music_audio(),
            )
            st.session_state.last_result_music_token = result_token
            return

    render_music(gameplay_music_audio())


def show_title_screen(local_storage):
    """Show the nickname and play-style choices on the opening screen."""
    background = title_image_data()

    st.markdown(
        f"""
        <style>
            .poker-title-screen {{
                min-height: 380px;
                border-radius: 8px;
                background-color: rgba(0, 35, 24, 0.28);
                background-image: url("data:image/png;base64,{background}");
                background-blend-mode: multiply;
                background-size: cover;
                background-position: center;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                align-items: center;
                padding: 54px 24px 24px;
                box-sizing: border-box;
                color: white;
                text-align: center;
                box-shadow: 0 6px 18px rgba(31, 41, 55, 0.2);
            }}
            .poker-title-screen h1 {{
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 3.2rem;
                letter-spacing: 0;
                line-height: 1.05;
                margin: 0;
                color: #ffffff;
                text-shadow: 0 2px 7px rgba(0, 0, 0, 0.6);
            }}
            .poker-title-screen p {{
                max-width: 480px;
                font-size: 1.15rem;
                font-weight: 600;
                margin-top: 14px;
                text-shadow: 0 2px 5px rgba(0, 0, 0, 0.7);
            }}
            @media (max-width: 600px) {{
                .poker-title-screen {{
                    min-height: 300px;
                    padding-top: 26px;
                }}
                .poker-title-screen h1 {{
                    font-size: 2.45rem;
                }}
            }}
        </style>
        <div class="poker-title-screen">
            <h1>Poker High Card</h1>
            <p>Choose the first dealer.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.toggle("Music", key="music_enabled")
    play_scene_music("title")

    st.text_input(
        "Your nickname",
        key="nickname",
        placeholder="Enter the name everyone calls you",
        max_chars=24,
        on_change=nickname_changed,
    )
    nickname_is_saved = st.session_state.get("nickname_saved", False)
    st.button(
        "Nickname remembered"
        if nickname_is_saved
        else "Remember nickname on this device",
        on_click=remember_nickname,
        args=(local_storage,),
        disabled=nickname_is_saved,
        use_container_width=True,
    )
    st.markdown("**Choose a play style**")
    modes_disabled = not nickname_is_saved

    private_column, table_column, judge_column = st.columns(3)
    with private_column:
        if st.button(
            "Private device",
            type="primary",
            disabled=modes_disabled,
            use_container_width=True,
        ):
            enter_play_mode(PRIVATE_DEVICE_MODE)

    with table_column:
        if st.button(
            "Table draw",
            disabled=modes_disabled,
            use_container_width=True,
        ):
            enter_play_mode(TABLE_MODE)

    with judge_column:
        if st.button(
            "Auto judge",
            disabled=modes_disabled,
            use_container_width=True,
        ):
            enter_play_mode(AUTO_JUDGE_MODE)


@st.cache_data
def card_image_data(rank, suit):
    """Load one matching card asset and encode it for the HTML image."""
    rank_name = CARD_RANK_NAMES.get(rank, rank)
    detail_suffix = "2" if rank in ["J", "Q", "K"] else ""
    filename = f"{rank_name}_of_{suit.lower()}{detail_suffix}.svg"
    card_path = CARD_ASSETS_DIR / filename
    return base64.b64encode(card_path.read_bytes()).decode("ascii")


def show_card(result, is_winner=False):
    """Display the matching card from one consistent classic deck."""
    card = result["card"]
    player_name = html.escape(result["player"])
    border_color = "#15803d" if is_winner else "#c8c8c8"
    winner_label = "Winner" if is_winner else "Drawn card"
    rank = card["rank"]
    suit = card["suit"]
    card_data = card_image_data(rank, suit)

    st.markdown(
        f"""
        <div style="text-align: center; margin: 8px 0 22px;">
            <div style="font-size: 1rem; color: #57606a;">{winner_label}</div>
            <div style="font-size: 1.15rem; font-weight: 700; margin: 2px 0 10px;">{player_name}</div>
            <img
                class="playing-card-image"
                src="data:image/svg+xml;base64,{card_data}"
                alt="{rank} of {suit}"
                style="
                    display: block;
                    box-sizing: border-box;
                    width: min(100%, 200px);
                    height: auto;
                    margin: 0 auto;
                    border: 3px solid {border_color};
                    border-radius: 8px;
                    background: #fffefb;
                    box-shadow: 0 5px 14px rgba(31, 41, 55, 0.18);
                "
            >
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_hidden_card(player_name):
    """Show a playing-card back without revealing the other player's card."""
    safe_name = html.escape(player_name)

    st.markdown(
        f"""
        <div style="text-align: center; margin: 8px 0 22px;">
            <div style="font-size: 1rem; color: #57606a;">Hidden card</div>
            <div style="font-size: 1.15rem; font-weight: 700; margin: 2px 0 10px;">{safe_name}</div>
            <div style="
                box-sizing: border-box;
                width: min(100%, 200px);
                aspect-ratio: 167 / 243;
                margin: 0 auto;
                border: 7px solid #fffefb;
                outline: 1px solid #b8b8b8;
                border-radius: 8px;
                background: #2456a6;
                box-shadow: 0 5px 14px rgba(31, 41, 55, 0.16);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #ffffff;
                font-family: Georgia, 'Times New Roman', serif;
            ">
                <div style="
                    width: calc(100% - 12px);
                    height: calc(100% - 12px);
                    border: 2px solid rgba(255, 255, 255, 0.85);
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 2.1rem;
                    line-height: 1.7;
                    letter-spacing: 0;
                ">♠ ♥<br>♦ ♣</div>
            </div>
            <div style="color: #57606a; font-size: 0.95rem; margin-top: 8px;">
                Only they can see the front
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_private_device_mode():
    """Let each player use their own browser and see only their own card."""
    st.subheader("Private Device Mode")
    st.info(
        "Everyone opens this app on their own device. Join the same table code, then each browser shows only that player's card."
    )

    if "private_player_id" not in st.session_state:
        st.session_state.private_player_id = secrets.token_hex(8)

    if "host_name" not in st.session_state:
        st.session_state.host_name = preferred_nickname("Host")
    if "join_name" not in st.session_state:
        st.session_state.join_name = preferred_nickname()

    # Older links included a private player ID. Remove it so each browser gets
    # its own identity instead of accidentally joining as the host.
    if "pid" in st.query_params:
        del st.query_params["pid"]

    table_code = st.session_state.get("private_table_code")
    shared_table_code = clean_table_code(st.query_params.get("table", ""))

    if table_code is None:
        joined_or_created = False
        setup_placeholder = st.empty()

        with setup_placeholder.container():
            create_column, join_column = st.columns(2)

            with create_column:
                st.markdown("**Create a table**")
                private_player_count = st.slider(
                    "Private table players",
                    min_value=2,
                    max_value=10,
                    value=6,
                    key="private_player_count",
                )
                host_name = st.text_input("Your name", key="host_name")

                if st.button("Create table", type="primary"):
                    clean_name = host_name.strip() or "Host"
                    create_private_table(private_player_count, clean_name)
                    table_code = st.session_state.private_table_code
                    joined_or_created = True

            with join_column:
                st.markdown("**Join a table**")
                join_code = st.text_input(
                    "Table code",
                    value=shared_table_code,
                    key="join_code",
                    max_chars=12,
                )
                join_name = st.text_input("Your name", key="join_name")

                if st.button("Join table"):
                    clean_name = join_name.strip() or "Player"
                    error = join_private_table(join_code, clean_name)

                    if error:
                        st.error(error)
                    else:
                        table_code = st.session_state.private_table_code
                        joined_or_created = True

        if not joined_or_created:
            play_scene_music("gameplay")
            return

        setup_placeholder.empty()

    tables = load_private_tables()
    table = tables.get(table_code)

    if table is None:
        play_scene_music("gameplay")
        st.warning(
            "This table code was not found. It may have expired after the app restarted or redeployed."
        )
        st.write("Create a new table and have everyone join the new code.")

        if st.button("Create or join another table", type="primary"):
            leave_private_table()
            st.rerun()

        return

    player_id = st.session_state.private_player_id
    current_player = None

    for player in table["players"]:
        if player["id"] == player_id:
            current_player = player

    if current_player is None:
        play_scene_music("gameplay")
        st.error("This browser is not joined to that table.")
        st.button("Leave table", on_click=leave_private_table)
        return

    if table["status"] == "dealt":
        result_token = f"private:{table_code}:{table.get('draw_id', 'dealt')}"
        play_scene_music("result", result_token)
    else:
        play_scene_music("gameplay")

    st.metric("Table code", table_code)
    st.caption(
        "Share this code or the current page URL. Each person must press Join table on their own device."
    )
    st.write(f"Players: {len(table['players'])} / {table['number_of_players']}")

    if table["status"] == "waiting":
        st.write("Waiting for everyone to join.")
        st.table(
            [
                {
                    "Player": player["name"],
                    "Status": "joined",
                }
                for player in table["players"]
            ]
        )

        is_host = table["host_id"] == player_id
        if is_host:
            if len(table["players"]) < table["number_of_players"]:
                players_needed = table["number_of_players"] - len(table["players"])
                st.warning(f"Waiting for {players_needed} more player(s) before dealing.")
            else:
                st.success("Everyone is seated. Deal cards when the table is ready.")

            if len(table["players"]) >= table["number_of_players"] and st.button("Deal cards", type="primary"):
                deal_private_table(table_code)
                st.rerun()
        else:
            st.caption("Press Refresh table to check whether the host has dealt.")

        if st.button("Refresh table"):
            st.rerun()

    else:
        st.subheader("Your Card")
        show_card({"player": current_player["name"], "card": current_player["card"]})

        st.subheader("Table")
        card_columns = st.columns(2)
        for index, player in enumerate(table["players"]):
            with card_columns[index % 2]:
                if player["id"] == player_id:
                    show_card({"player": player["name"], "card": player["card"]})
                else:
                    show_hidden_card(player["name"])

        if table["host_id"] == player_id:
            if st.button("Redeal same table"):
                redeal_private_table(table_code)
                st.rerun()

    st.button("Leave table on this device", on_click=leave_private_table)


st.set_page_config(page_title="Poker High Card", page_icon="🂡", layout="centered")

local_storage = LocalStorage(key="poker_high_card_storage")
if "music_defaults_v2_applied" not in st.session_state:
    # Start quietly. Music plays only after the visitor turns it on.
    st.session_state.music_enabled = False
    st.session_state.music_defaults_v2_applied = True

if "nickname" not in st.session_state:
    stored_nickname = local_storage.getItem(NICKNAME_STORAGE_KEY)
    st.session_state.nickname = (
        stored_nickname.strip()
        if isinstance(stored_nickname, str) and stored_nickname.strip()
        else ""
    )
    st.session_state.nickname_saved = bool(st.session_state.nickname)
elif "nickname_saved" not in st.session_state:
    st.session_state.nickname_saved = bool(preferred_nickname(""))

if not st.session_state.get("title_screen_complete"):
    show_title_screen(local_storage)
    st.stop()

st.title("Poker High Card")
st.write("Draw one card for each player to decide the first dealer or button.")

with st.sidebar:
    if st.button("Back to title", use_container_width=True):
        st.session_state.title_screen_complete = False
        st.rerun()

    st.toggle("Music", key="music_enabled")

    st.header("Rules")
    st.write("Highest rank wins. If ranks tie, the highest suit wins.")
    st.write("Rank: A > K > Q > J > 10 > 9 > ... > 2")
    st.write("Suit: Spades > Hearts > Diamonds > Clubs")
    st.link_button(
        "Share on LinkedIn",
        LINKEDIN_SHARE_URL,
        use_container_width=True,
    )

app_mode = st.radio(
    "Play style",
    PLAY_MODES,
    key="play_style",
    help="Private device mode shows each player only their own card. Table mode shows all cards without judging. Auto judge shows the winner and ranking.",
)

if app_mode == PRIVATE_DEVICE_MODE:
    render_private_device_mode()
    st.stop()

number_of_players = st.slider("Number of players", min_value=2, max_value=10, value=6)

# If the player count changes, clear old results so the draw always matches the table.
if st.session_state.get("previous_number_of_players") != number_of_players:
    reset_draw()
    st.session_state.previous_number_of_players = number_of_players

player_names = []
for player_number in range(1, number_of_players + 1):
    player_key = f"player_name_{player_number}"
    if player_key not in st.session_state:
        st.session_state[player_key] = (
            preferred_nickname()
            if player_number == 1
            else f"Player {player_number}"
        )

    name = st.text_input(f"Player {player_number} name", key=player_key)

    # If a name is blank, use a simple default so the results always display clearly.
    player_names.append(name.strip() or f"Player {player_number}")

if len(set(player_names)) < len(player_names):
    st.warning("Some players have the same name. The draw will still work, but unique names are easier to read.")

draw_button, reset_button = st.columns(2)

with draw_button:
    if st.button("Draw cards", type="primary"):
        st.session_state.results = draw_cards(player_names)
        st.session_state.draw_id = secrets.token_hex(6)
        st.rerun()

with reset_button:
    st.button("Reset", on_click=reset_draw)

if "results" in st.session_state:
    play_scene_music("result", st.session_state.get("draw_id"))
else:
    play_scene_music("gameplay")

if "results" in st.session_state:
    results = st.session_state.results

    if app_mode == TABLE_MODE:
        st.subheader("Table Draw")
        st.info("Everyone drew from the same shuffled deck. Compare the cards together at the table.")

        card_columns = st.columns(2)
        for index, result in enumerate(results):
            with card_columns[index % 2]:
                show_card(result)

        st.caption("No automatic winner is shown in Table mode.")

    else:
        winner = find_winner(results)
        ranked_results = sort_results_by_strength(results)
        nickname = preferred_nickname()
        is_my_win = winner == results[0]

        if is_my_win:
            safe_nickname = html.escape(nickname)
            st.markdown(
                f"""
                <div style="
                    padding: 24px 16px;
                    margin: 12px 0 20px;
                    background: #166534;
                    color: #ffffff;
                    border: 3px solid #f5c542;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 2rem;
                    font-weight: 800;
                    line-height: 1.25;
                ">{safe_nickname}が一位だよ！</div>
                """,
                unsafe_allow_html=True,
            )

            draw_id = st.session_state.get("draw_id")
            if (
                draw_id
                and st.session_state.get("celebrated_draw_id") != draw_id
            ):
                st.balloons()
                st.session_state.celebrated_draw_id = draw_id

        st.subheader("Winner")

        winning_card = winner["card"]
        st.success(f"{winner['player']} wins with {format_card(winning_card)}.")
        st.caption(
            "This card wins because cards are compared by rank first, then by suit if ranks are tied."
        )

        st.subheader("Cards Drawn")

        card_columns = st.columns(2)
        for index, result in enumerate(results):
            with card_columns[index % 2]:
                show_card(result, is_winner=result == winner)

        st.subheader("Ranking")

        table_rows = []
        for position, result in enumerate(ranked_results, start=1):
            card = result["card"]
            table_rows.append(
                {
                    "Place": position,
                    "Player": result["player"],
                    "Card": format_card(card),
                    "Comparison": strength_label(card),
                }
            )

        st.dataframe(table_rows, hide_index=True, use_container_width=True)
