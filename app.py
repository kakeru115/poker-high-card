import base64
import html
import json
import random
import re
import secrets
import string
from pathlib import Path

import streamlit as st
from filelock import FileLock


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

RED_SUITS = ["Hearts", "Diamonds"]

AUTO_JUDGE_MODE = "Auto judge"
TABLE_MODE = "Table mode"
PRIVATE_DEVICE_MODE = "Private device mode"

TABLES_FILE = Path("private_tables.json")
TABLES_TEMP_FILE = Path("private_tables.tmp")
TABLES_LOCK = FileLock("private_tables.lock", timeout=5)
TITLE_IMAGE = Path("assets/poker-title.png")

PIP_POSITIONS = {
    "2": [(50, 27), (50, 73)],
    "3": [(50, 23), (50, 50), (50, 77)],
    "4": [(31, 27), (69, 27), (31, 73), (69, 73)],
    "5": [(31, 25), (69, 25), (50, 50), (31, 75), (69, 75)],
    "6": [(31, 23), (69, 23), (31, 50), (69, 50), (31, 77), (69, 77)],
    "7": [(31, 20), (69, 20), (50, 36), (31, 50), (69, 50), (31, 80), (69, 80)],
    "8": [(31, 18), (69, 18), (50, 35), (31, 43), (69, 43), (50, 65), (31, 82), (69, 82)],
    "9": [(31, 18), (69, 18), (31, 39), (69, 39), (50, 50), (31, 61), (69, 61), (31, 82), (69, 82)],
    "10": [(31, 16), (69, 16), (50, 31), (31, 38), (69, 38), (31, 62), (69, 62), (50, 69), (31, 84), (69, 84)],
}


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


def card_color(card):
    """Use red for hearts and diamonds, and dark text for black suits."""
    if card["suit"] in RED_SUITS:
        return "#b42318"

    return "#1f2937"


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


def show_title_screen():
    """Show a simple opening screen before the play-style controls."""
    background = title_image_data()

    st.markdown(
        f"""
        <style>
            .poker-title-screen {{
                min-height: 500px;
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
                padding: 70px 24px 24px;
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
                    min-height: 430px;
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

    if st.button("Tap to play", type="primary", use_container_width=True):
        st.session_state.title_screen_complete = True
        st.rerun()


def card_center_html(rank, symbol):
    """Build the middle of a card with classic pips or a face-card panel."""
    if rank == "A":
        return f'<div class="card-ace">{symbol}</div>'

    if rank in ["J", "Q", "K"]:
        return (
            f'<div class="face-card"><div>{symbol}</div>'
            f"<strong>{rank}</strong><div>{symbol}</div></div>"
        )

    pips = []
    for left, top in PIP_POSITIONS[rank]:
        rotation = "rotate(180deg)" if top > 50 else "none"
        pips.append(
            f'<span class="card-pip" style="left:{left}%; top:{top}%; '
            f'transform:translate(-50%, -50%) {rotation};">{symbol}</span>'
        )

    return "".join(pips)


def show_card(result, is_winner=False):
    """Display one player's card as a familiar paper playing card."""
    card = result["card"]
    player_name = html.escape(result["player"])
    border_color = "#15803d" if is_winner else "#c8c8c8"
    winner_label = "Winner" if is_winner else "Drawn card"
    rank = card["rank"]
    symbol = SUIT_SYMBOLS[card["suit"]]
    color = card_color(card)
    center = card_center_html(rank, symbol)

    st.markdown(
        f"""
        <style>
            .playing-card {{
                position: relative;
                box-sizing: border-box;
                width: min(100%, 210px);
                aspect-ratio: 5 / 7;
                margin: 0 auto;
                border-radius: 8px;
                background: #fffefb;
                box-shadow: 0 5px 14px rgba(31, 41, 55, 0.18);
                font-family: Georgia, 'Times New Roman', serif;
            }}
            .card-corner {{
                position: absolute;
                font-size: 2rem;
                font-weight: 700;
                line-height: 0.82;
                z-index: 2;
            }}
            .card-corner span {{
                display: block;
                font-size: 1.55rem;
                margin-top: 8px;
            }}
            .card-pip {{
                position: absolute;
                font-size: 2.2rem;
                line-height: 1;
            }}
            .card-ace {{
                position: absolute;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 6.2rem;
            }}
            .face-card {{
                position: absolute;
                inset: 24% 25%;
                border: 2px solid currentColor;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: space-around;
                font-size: 2rem;
                line-height: 1;
            }}
            .face-card strong {{
                font-size: 4.4rem;
            }}
        </style>
        <div style="text-align: center; margin: 8px 0 22px;">
            <div style="font-size: 1rem; color: #57606a;">{winner_label}</div>
            <div style="font-size: 1.15rem; font-weight: 700; margin: 2px 0 10px;">{player_name}</div>
            <div class="playing-card" style="
                border: 2px solid {border_color};
                color: {color};
            ">
                <div class="card-corner" style="
                    top: 10px;
                    left: 11px;
                ">
                    <div>{rank}</div>
                    <span>{symbol}</span>
                </div>
                {center}
                <div class="card-corner" style="
                    right: 11px;
                    bottom: 10px;
                    transform: rotate(180deg);
                ">
                    <div>{rank}</div>
                    <span>{symbol}</span>
                </div>
            </div>
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
                width: min(100%, 210px);
                aspect-ratio: 5 / 7;
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
                host_name = st.text_input("Your name", value="Host", key="host_name")

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
                join_name = st.text_input("Your name", value="Player", key="join_name")

                if st.button("Join table"):
                    clean_name = join_name.strip() or "Player"
                    error = join_private_table(join_code, clean_name)

                    if error:
                        st.error(error)
                    else:
                        table_code = st.session_state.private_table_code
                        joined_or_created = True

        if not joined_or_created:
            return

        setup_placeholder.empty()

    tables = load_private_tables()
    table = tables.get(table_code)

    if table is None:
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
        st.error("This browser is not joined to that table.")
        st.button("Leave table", on_click=leave_private_table)
        return

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

if not st.session_state.get("title_screen_complete"):
    show_title_screen()
    st.stop()

st.title("Poker High Card")
st.write("Draw one card for each player to decide the first dealer or button.")

with st.sidebar:
    if st.button("Back to title", use_container_width=True):
        st.session_state.title_screen_complete = False
        st.rerun()

    st.header("Rules")
    st.write("Highest rank wins. If ranks tie, the highest suit wins.")
    st.write("Rank: A > K > Q > J > 10 > 9 > ... > 2")
    st.write("Suit: Spades > Hearts > Diamonds > Clubs")

app_mode = st.radio(
    "Play style",
    [PRIVATE_DEVICE_MODE, TABLE_MODE, AUTO_JUDGE_MODE],
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
    name = st.text_input(f"Player {player_number} name", value=f"Player {player_number}")

    # If a name is blank, use a simple default so the results always display clearly.
    player_names.append(name.strip() or f"Player {player_number}")

if len(set(player_names)) < len(player_names):
    st.warning("Some players have the same name. The draw will still work, but unique names are easier to read.")

draw_button, reset_button = st.columns(2)

with draw_button:
    if st.button("Draw cards", type="primary"):
        st.session_state.results = draw_cards(player_names)

with reset_button:
    st.button("Reset", on_click=reset_draw)

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
