import html
import random

import streamlit as st


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


def find_winner(results):
    """Find the player with the strongest high card."""
    return max(results, key=lambda result: card_strength(result["card"]))


def sort_results_by_strength(results):
    """Show strongest cards first in the ranking table."""
    return sorted(results, key=lambda result: card_strength(result["card"]), reverse=True)


def reset_draw():
    """Clear the current draw and return the app to its starting state."""
    st.session_state.pop("results", None)


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
    [TABLE_MODE, AUTO_JUDGE_MODE],
    horizontal=True,
    help="Table mode shows the cards only. Auto judge also shows the winner and ranking.",
)

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
