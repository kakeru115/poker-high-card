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


def find_winner(results):
    """Find the player with the strongest high card."""
    return max(results, key=lambda result: card_strength(result["card"]))


def reset_draw():
    """Clear the current draw and return the app to its starting state."""
    st.session_state.pop("results", None)


st.set_page_config(page_title="Poker High Card", page_icon="🂡")

st.title("Poker High Card")
st.write("Draw one card for each player to decide the first dealer or button.")

number_of_players = st.slider("Number of players", min_value=2, max_value=10, value=6)

player_names = []
for player_number in range(1, number_of_players + 1):
    name = st.text_input(f"Player {player_number} name", value=f"Player {player_number}")

    # If a name is blank, use a simple default so the results always display clearly.
    player_names.append(name.strip() or f"Player {player_number}")

draw_button, reset_button = st.columns(2)

with draw_button:
    if st.button("Draw cards", type="primary"):
        st.session_state.results = draw_cards(player_names)

with reset_button:
    st.button("Reset", on_click=reset_draw)

if "results" in st.session_state:
    results = st.session_state.results
    winner = find_winner(results)

    st.subheader("Cards Drawn")

    for result in results:
        card = result["card"]
        st.write(f"**{result['player']}**: {format_card(card)}")

    winning_card = format_card(winner["card"])
    st.success(f"Winner: {winner['player']} with {winning_card}")
