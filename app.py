import html
import json
import random
import secrets
import string
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


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
WAITING_REFRESH_SECONDS = 10


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
    if not TABLES_FILE.exists():
        return {}

    with TABLES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_private_tables(tables):
    """Save private tables so different browsers can share the same table."""
    with TABLES_FILE.open("w", encoding="utf-8") as file:
        json.dump(tables, file, indent=2)


def make_table_code():
    """Create a short table code that is easy to read aloud."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def create_private_table(number_of_players, host_name):
    """Create a new private table and add the host as the first player."""
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
    st.query_params["pid"] = player_id


def join_private_table(table_code, player_name):
    """Join an existing private table from a different browser session."""
    tables = load_private_tables()
    table = tables.get(table_code)

    if table is None:
        return "That table code was not found."

    if table["status"] == "dealt":
        return "Cards have already been dealt for that table."

    player_id = st.session_state.private_player_id
    for player in table["players"]:
        if player["id"] == player_id:
            player["name"] = player_name
            save_private_tables(tables)
            st.session_state.private_table_code = table_code
            st.query_params["table"] = table_code
            st.query_params["pid"] = player_id
            return None

    if len(table["players"]) >= table["number_of_players"]:
        return "That table is already full."

    table["players"].append({"id": player_id, "name": player_name, "card": None})
    save_private_tables(tables)
    st.session_state.private_table_code = table_code
    st.query_params["table"] = table_code
    st.query_params["pid"] = player_id
    return None


def deal_private_table(table_code):
    """Deal one card to every player in a private table."""
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


def refresh_waiting_table():
    """Refresh waiting private tables so every device sees joins and deals."""
    components.html(
        f"""
        <script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {WAITING_REFRESH_SECONDS * 1000});
        </script>
        """,
        height=0,
    )


def show_card(result, is_winner=False):
    """Display one player's card as a small card-style panel."""
    card = result["card"]
    player_name = html.escape(result["player"])
    border_color = "#0f766e" if is_winner else "#d0d7de"
    background = "#ecfdf5" if is_winner else "#ffffff"
    winner_label = "Winner" if is_winner else "Drawn card"

    st.markdown(
        f"""
        <div style="
            border: 1px solid {border_color};
            border-radius: 8px;
            background: {background};
            padding: 14px;
            min-height: 150px;
        ">
            <div style="font-size: 0.85rem; color: #57606a;">{winner_label}</div>
            <div style="font-weight: 700; margin-top: 4px;">{player_name}</div>
            <div style="
                color: {card_color(card)};
                font-size: 2.4rem;
                font-weight: 800;
                line-height: 1.1;
                margin-top: 14px;
            ">{card['rank']} {SUIT_SYMBOLS[card['suit']]}</div>
            <div style="color: #57606a; margin-top: 8px;">{card['suit']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_hidden_card(player_name):
    """Show another player's card slot without revealing their actual card."""
    safe_name = html.escape(player_name)

    st.markdown(
        f"""
        <div style="
            border: 1px solid #d0d7de;
            border-radius: 8px;
            background: #f6f8fa;
            padding: 14px;
            min-height: 150px;
        ">
            <div style="font-size: 0.85rem; color: #57606a;">Hidden card</div>
            <div style="font-weight: 700; margin-top: 4px;">{safe_name}</div>
            <div style="
                color: #57606a;
                font-size: 2.4rem;
                font-weight: 800;
                line-height: 1.1;
                margin-top: 14px;
            ">??</div>
            <div style="color: #57606a; margin-top: 8px;">Only they can see it</div>
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
        st.session_state.private_player_id = st.query_params.get("pid", secrets.token_hex(8))

    if "private_table_code" not in st.session_state and "table" in st.query_params:
        st.session_state.private_table_code = st.query_params["table"].upper()

    table_code = st.session_state.get("private_table_code")

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
                join_code = st.text_input("Table code", key="join_code").upper().strip()
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
        st.error("This table no longer exists.")
        st.button("Leave table", on_click=leave_private_table)
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
    st.write(f"Players: {len(table['players'])} / {table['number_of_players']}")

    if table["status"] == "waiting":
        if len(table["players"]) >= table["number_of_players"]:
            deal_private_table(table_code)
            st.rerun()

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
            if len(table["players"]) < 2:
                st.warning("At least two players are needed before dealing.")
            else:
                st.caption(
                    "Cards will deal automatically when the table is full. You can also start now."
                )

            if len(table["players"]) >= 2 and st.button("Start now", type="primary"):
                deal_private_table(table_code)
                st.rerun()
        else:
            st.caption("This page refreshes while waiting. Cards will appear when the host starts or the table fills.")

        refresh_waiting_table()

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

st.title("Poker High Card")
st.write("Draw one card for each player to decide the first dealer or button.")

with st.sidebar:
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
