# Poker High Card

Poker High Card is a small Streamlit app that helps a poker table decide the first dealer or button position. Each player draws one card, and the strongest card wins.

Live app: https://poker-high-card.streamlit.app/

## Features

- Choose 2 to 10 players.
- Enter custom player names.
- Build a standard 52-card deck.
- Draw one unique card per player.
- Choose Private device mode so each person can join from their own browser and see only their own card.
- Choose Table mode to show cards only and let everyone judge together.
- Choose Auto judge mode to show the winner and ranking automatically.
- Compare cards by poker high-card rules.
- Break rank ties by suit.
- Show every player's card in an easy-to-scan card layout.
- Highlight the winner.
- Show a ranked results table with comparison details.
- Warn when multiple players have the same name.
- Reset the draw and start again.

## Card Strength

Ranks are compared in this order:

`A > K > Q > J > 10 > 9 > 8 > 7 > 6 > 5 > 4 > 3 > 2`

If two players draw the same rank, suits are compared in this order:

`Spades > Hearts > Diamonds > Clubs`

## Tech Stack

- Python
- Streamlit

## How to Run

Install the dependency:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal.

For Private device mode, have each player open the app from their own device or browser session. The host creates a table code, everyone joins that same code, and each player sees only their own card. Cards are dealt automatically when the table is full, or the host can start once at least two players have joined.

Private table codes are temporary. If the app restarts or redeploys, create a new table and share the new code.

## GitHub

This project is ready to publish to GitHub. It includes:

- `.gitignore` to keep Python cache files, virtual environments, local secrets, and macOS metadata out of the repository.
- GitHub Actions workflow at `.github/workflows/python-check.yml`.

The workflow installs dependencies and checks that `app.py` has valid Python syntax whenever code is pushed or a pull request is opened.
