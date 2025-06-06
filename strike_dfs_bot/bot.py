import discord
from discord import ui, ButtonStyle
import requests
import os
import re
import openai
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from difflib import get_close_matches
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime

# Environment setup
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Data initialization
csv_path = os.path.join(os.path.dirname(__file__), "betting_events_rows.csv")
df = pd.read_csv(csv_path)
betting_events = df.to_dict(orient="records")

# API clients
client_ai = openai.OpenAI(api_key=OPENAI_API_KEY)

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# User state tracking
verified_users = set()
login_notified_users = set()
user_modes = {}
user_carts = {}
incomplete_bets = {}
user_login_attempts = {}
user_nlp_bet_state = {}

async def handle_verification(message):
    user_id = str(message.author.id)
    channel = message.channel

async def show_main_menu(message, user_id):
    user_modes[user_id] = None
    # Show buttons instead of text instructions
    await message.channel.send("Main Menu:", view=MainMenuView())

async def handle_search_query(message, user_id):
    await handle_search_mode(user_id, message, message.channel)



# Template dictionary to store in-progress bets per user
guided_bet_state = defaultdict(dict)


def generate_player_stat_image(player_name, filename="player_stats_preview.png"):
    player_df = df[df["player_name"].str.lower() == player_name.lower()]
    if player_df.empty:
        return None

    # Set the style for the plot
    plt.style.use('ggplot')
    
    # Create figure with a dark background
    fig, ax = plt.subplots(figsize=(10, min(0.5 * len(player_df) + 1, 20)))
    fig.patch.set_facecolor('#2C2F33')  # Discord-like dark background
    ax.set_facecolor('#2C2F33')
    ax.axis('off')
    
    # Add a title with player name and NBA styling
    ax.set_title(f"{player_name}'s Prop Betting Lines", fontsize=16, color='white', fontweight='bold', pad=20)
    
    # Table formatting
    table_data = player_df[["stat_type", "line_value", "opponent"]].values.tolist()
    table = ax.table(
        cellText=table_data,
        colLabels=["Stat Type", "Line", "Opponent"],
        loc='center',
        cellLoc='center',
        colWidths=[0.4, 0.2, 0.4]  # Adjust column widths for better proportions
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)
    
    # Style header row with NBA team colors (using Lakers purple and gold)
    header_color = '#552583'  # Lakers purple
    header_text_color = '#FDB927'  # Lakers gold
    
    for col in range(3):
        cell = table[0, col]
        cell.set_facecolor(header_color)
        cell.set_text_props(color=header_text_color, weight='bold')
        cell.set_edgecolor('white')
    
    # Style data rows with alternating colors
    for row in range(1, len(table_data) + 1):
        row_color = '#36393F' if row % 2 == 0 else '#40444B'  # Discord-like alternating row colors
        
        for col in range(3):
            cell = table[row, col]
            cell.set_facecolor(row_color)
            cell.set_text_props(color='white')
            cell.set_edgecolor('#23272A')  # Darker border color
    
    # Add a subtle border around the entire table
    for pos, cell in table._cells.items():
        cell.set_linewidth(0.5)
    
    # Add a subtle player note at the bottom
    fig.text(
        0.5, 0.02, 
        f"StrikeBot • {player_name} Props", 
        ha='center', 
        color='#FDB927', 
        alpha=0.7,
        fontsize=10,
        fontweight='bold'
    )
    
    # Save with high quality
    plt.savefig(filename, bbox_inches='tight', dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    return filename


def resolve_player_name(user_input):
    try:
        prompt = f"""
You are an NBA player nickname resolver. Match user input to full player names. 

STRICT RULES:
1. ONLY return a player name if the input is clearly referring to an NBA player
2. Do NOT return anything for generic terms like "goat", "best player", etc. unless they are part of a player's established nickname
3. Do NOT return anything if you're not highly confident it's referring to a specific player
4. Return EMPTY STRING if the input doesn't clearly refer to an NBA player

List of valid NBA players:
{json.dumps(df["player_name"].unique().tolist(), indent=2)}

User Input: "{user_input}"

Your task: Return ONLY the best matching full player name from the list above. Return as a plain string, no markdown, no explanations. If no clear match, return an empty string.
"""

        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        name = response.choices[0].message.content.strip()
        # Check if it's in the actual player list to avoid hallucination
        if name and name in df["player_name"].values:
            return name
        return None
    except Exception as e:
        print("❌ GPT nickname resolution error:", e)
        return None


def resolve_team_name(user_input):
    """Identify NBA team from user input and return current roster players."""
    try:
        # NBA team mappings by conference
        eastern_teams = {
            "atlanta": "ATL", "hawks": "ATL", "atl": "ATL",
            "boston": "BOS", "celtics": "BOS", "bos": "BOS",
            "brooklyn": "BKN", "nets": "BKN", "bkn": "BKN",
            "charlotte": "CHA", "hornets": "CHA", "cha": "CHA",
            "chicago": "CHI", "bulls": "CHI", "chi": "CHI",
            "cleveland": "CLE", "cavaliers": "CLE", "cavs": "CLE", "cle": "CLE",
            "detroit": "DET", "pistons": "DET", "det": "DET",
            "indiana": "IND", "pacers": "IND", "ind": "IND",
            "miami": "MIA", "heat": "MIA", "mia": "MIA",
            "milwaukee": "MIL", "bucks": "MIL", "mil": "MIL",
            "new york": "NYK", "knicks": "NYK", "nyk": "NYK",
            "orlando": "ORL", "magic": "ORL", "orl": "ORL",
            "philadelphia": "PHI", "76ers": "PHI", "sixers": "PHI", "phi": "PHI",
            "toronto": "TOR", "raptors": "TOR", "tor": "TOR",
            "washington": "WAS", "wizards": "WAS", "was": "WAS",
        }
        
        western_teams = {
            "dallas": "DAL", "mavericks": "DAL", "mavs": "DAL", "dal": "DAL",
            "denver": "DEN", "nuggets": "DEN", "den": "DEN",
            "golden state": "GSW", "warriors": "GSW", "gsw": "GSW", "gs": "GSW",
            "houston": "HOU", "rockets": "HOU", "hou": "HOU",
            "los angeles clippers": "LAC", "clippers": "LAC", "lac": "LAC",
            "los angeles lakers": "LAL", "lakers": "LAL", "lal": "LAL",
            "memphis": "MEM", "grizzlies": "MEM", "mem": "MEM",
            "minnesota": "MIN", "timberwolves": "MIN", "wolves": "MIN", "min": "MIN",
            "new orleans": "NOP", "pelicans": "NOP", "pels": "NOP", "nop": "NOP",
            "oklahoma city": "OKC", "thunder": "OKC", "okc": "OKC",
            "phoenix": "PHX", "suns": "PHX", "phx": "PHX",
            "portland": "POR", "trail blazers": "POR", "blazers": "POR", "por": "POR",
            "sacramento": "SAC", "kings": "SAC", "sac": "SAC",
            "san antonio": "SAS", "spurs": "SAS", "sas": "SAS",
            "utah": "UTA", "jazz": "UTA", "uta": "UTA"
        }
        
        team_mappings = {**eastern_teams, **western_teams}
        user_input_lower = user_input.lower()
        
        # Direct mapping check
        for team_term, team_code in team_mappings.items():
            if team_term in user_input_lower:
                return get_team_players(team_code)
        
        # Fallback to AI-based team resolution
        prompt = f"""You are an NBA team name resolver. Given a user input, determine if it refers to an NBA team.

User Input: "{user_input}"

If the input refers to an NBA team, return ONLY the team's 3-letter code (e.g., LAL, GSW, BOS).
If it doesn't clearly refer to an NBA team, return an empty string."""
        
        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        team_code = response.choices[0].message.content.strip()
        if team_code and len(team_code) == 3:
            return get_team_players(team_code)
        
        return None
    except Exception as e:
        print(f"Team resolution error: {e}")
        return None


def get_team_players(team_code):
    """Get current roster players for an NBA team."""
    try:
        prompt = f"""You are an NBA team roster expert. Given a team, return the players who CURRENTLY play for that team.

Team: {team_code}

List of all players in the dataset:
{json.dumps(df["player_name"].unique().tolist(), indent=2)}

Your task: Return ONLY a JSON list of player names who currently play for {team_code}. 
Format: ["Player Name 1", "Player Name 2", ...]
Only include players who are in the provided list and currently on the team's roster."""
        
        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Extract JSON from code blocks if present
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text[3:-3].strip()
        
        team_players = json.loads(response_text)
        if team_players and isinstance(team_players, list):
            valid_players = [p for p in team_players if p in df["player_name"].values]
            if valid_players:
                return {"team": team_code, "players": valid_players}
    except Exception as e:
        print(f"Error getting team players: {e}")
    
    return None


async def handle_guided_bet(message, user_id, channel):
    import re
    user_input = message.content.strip()
    state = guided_bet_state[user_id]
    user_cart = user_carts.setdefault(user_id, [])

    # Cart commands
    if user_input.lower() == "exit":
        user_modes[user_id] = None
        guided_bet_state[user_id] = {}
        await channel.send("🚪 Exited betting mode.")
        # Show main menu
        await channel.send("Main Menu:", view=MainMenuView())
        return

    if user_input.lower() == "search":
        user_modes[user_id] = "search"
        guided_bet_state[user_id] = {}
        await channel.send("🔍 Search Mode Activated! Type a team name, player, or stat (e.g., `Warriors`, `LeBron`, `points`).")
        # Add exit button
        await channel.send("Click the button below to exit:", view=ExitSearchView())
        return

    if user_input.lower() == "delete":
        user_carts[user_id] = []
        guided_bet_state[user_id] = {}
        await channel.send("🗑️ Cart cleared! Start over with `place bets`.")
        return

    if user_input.lower() == "confirm":
        if not user_cart:
            await channel.send("🛒 Your cart is empty. Add a bet first using `place bets`.")
            return

        # Show preview before entering bet amount
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]

        preview_image = generate_bet_confirmation_image(display_data, entry_fee="Pending", filename="cart_preview_confirming.png")
        await channel.send(file=discord.File(preview_image))
        state["step"] = "entry_fee"
        await channel.send("💰 Please type the **total bet amount** you'd like to place across all these picks (e.g., `20`).\nType `exit` to cancel.")
        return

    if state.get("step") == "entry_fee":
        try:
            cleaned = re.sub(r"[^\d.]", "", user_input)
            amount = float(cleaned)
            if amount <= 0:
                raise ValueError("Amount must be positive.")

            display_data = [
                {
                    "name": bet["player_name"],
                    "stat_type": bet["stat_type"],
                    "line_value": bet["line_value"],
                    "bet_type": bet["bet_type"]
                }
                for bet in user_cart
            ]
            cart_image = generate_bet_confirmation_image(display_data, amount, filename="cart_summary.png")
            await channel.send(file=discord.File(cart_image))
            payload = generate_bets_payload(user_id, amount, user_cart)
            await channel.send("✅ Bets confirmed and placed! Cart is now cleared.\n Type `place bets` to make more picks.")
            await channel.send(f"📦 Final payload sent to Strike API:\n```json\n{json.dumps(payload, indent=2)}\n```")
            user_carts[user_id] = []
            guided_bet_state[user_id] = {}
        except Exception as e:
            await channel.send(f"❌ Invalid amount. Please enter a number like `10` or `25`.\nError: {e}\n➡️ Type `exit` to cancel.")
        return

    if user_input.lower() == "add" and state.get("step") == "amount":
        await channel.send("⚠️ Please finish your current bet first.\n➡️ Type `exit` to cancel.")
        return

    step = state.get("step")
    if not step:
        state["step"] = "player"
        await channel.send("👤 Let's build your bet!\nPlease type the **name of the player** you want to bet on (e.g., `Curry`, `LeBron`).\n📌 Type `exit` to cancel anytime. Type `delete` to reset cart.")
        return

    if step == "player":
        player_names = df["player_name"].unique()
        matched = get_close_matches(user_input, player_names, n=1, cutoff=0.6)
        resolved_name = matched[0] if matched else resolve_player_name(user_input)

        if resolved_name and resolved_name in df["player_name"].values:
            state["player_name"] = resolved_name
            state["step"] = "stat"
            image_path = generate_player_stat_image(resolved_name)
            if image_path:
                await channel.send(file=discord.File(image_path))
            await channel.send(f"✅ Player selected: **{resolved_name}**\nNow type the **stat** you want to bet on (e.g., `points`, `rebounds`, `assists`).\n➡️ Type `exit` to cancel.")
        else:
            await channel.send("❌ Player not found. Please try again with a valid NBA player name.\n➡️ Type `exit` to cancel.")
        return

    if step == "stat":
        valid_stats = df[df["player_name"] == state["player_name"]]["stat_type"].unique()
        matched = get_close_matches(user_input.lower(), [s.lower() for s in valid_stats], n=1, cutoff=0.6)
        if matched:
            state["stat_type"] = matched[0]
            lines = df[(df["player_name"] == state["player_name"]) &
                       (df["stat_type"].str.lower() == matched[0])]["line_value"].unique()
            state["valid_lines"] = lines.tolist()
            state["step"] = "line"
            await channel.send(f"✅ Stat selected: **{matched[0]}**\nPlease type the **line value** you want (e.g., `{lines[0]}`).\n➡️ Type `exit` to cancel.")
        else:
            await channel.send(f"❌ Stat not found. Try one of these: {', '.join(valid_stats)}\n➡️ Type `exit` to cancel.")
        return

    if step == "line":
        try:
            val = float(user_input)
            if val in state.get("valid_lines", []):
                state["line_value"] = val
                state["step"] = "type"
                await channel.send("✅ Line value set!\nWould you like to bet `over` or `under`?\n➡️ Type `exit` to cancel.")
            else:
                await channel.send(f"❌ That line isn’t available. Try one of: {', '.join(map(str, state['valid_lines']))}\n➡️ Type `exit` to cancel.")
        except:
            await channel.send("❌ Invalid input. Please type a number like `23.5`.")
        return

    if step == "type":
        if user_input.lower() in ["over", "under"]:
            state["bet_type"] = user_input.lower()
            bet = {
                "entry_fee": 0,
                "player_name": state["player_name"],
                "bet_type": state["bet_type"],
                "line_value": state["line_value"],
                "stat_type": state["stat_type"]
            }
            user_cart.append(bet)
            guided_bet_state[user_id] = {}
            await channel.send("✅ Bet added to cart!")
            await channel.send("Type `add` to make another bet, or `confirm` to lock them in and set your wager.\n➡️ Type `exit` to cancel.")
        else:
            await channel.send("❌ Please type `over` or `under`.\n➡️ Type `exit` to cancel.")
        return





def generate_bet_confirmation_image(bets_data, entry_fee, filename="bet_confirmation.png"):
    import matplotlib.image as mpimg
    from PIL import Image

    # Set the style for the plot
    plt.style.use('ggplot')

    # Step 1: Generate main table image with modern styling
    column_titles = ["Player", "Stat Type", "Line", "Bet Type"]
    table_data = [
        [b["name"], b["stat_type"], b["line_value"], b["bet_type"]]
        for b in bets_data
    ]

    # Create figure with a dark background
    fig, ax = plt.subplots(figsize=(10, min(0.6 * len(table_data) + 1.5, 20)))
    fig.patch.set_facecolor('#2C2F33')  # Discord-like dark background
    ax.set_facecolor('#2C2F33')
    ax.axis('off')

    # Create the table with custom styling
    table = ax.table(
        cellText=table_data,
        colLabels=column_titles,
        loc='center',
        cellLoc='center',
        colWidths=[0.3, 0.3, 0.15, 0.25]  # Adjust column widths for better proportions
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)

    # Style header row with a green theme for confirmation
    header_color = '#1E8449'  # Dark green
    header_text_color = '#FFFFFF'  # White text
    
    for col in range(len(column_titles)):
        cell = table[0, col]
        cell.set_facecolor(header_color)
        cell.set_text_props(color=header_text_color, weight='bold')
        cell.set_edgecolor('white')

    # Style data rows with alternating colors
    for row in range(1, len(table_data) + 1):
        row_color = '#36393F' if row % 2 == 0 else '#40444B'  # Discord-like alternating row colors
        
        for col in range(len(column_titles)):
            cell = table[row, col]
            cell.set_facecolor(row_color)
            cell.set_text_props(color='white')
            cell.set_edgecolor('#23272A')  # Darker border color

    # Add a subtle border around the entire table
    for pos, cell in table._cells.items():
        cell.set_linewidth(0.5)

    # Set title with entry fee information if provided
    title = "Bet Confirmation"
    if entry_fee is not None:
        title = f"Bet Confirmation - ${entry_fee}"
    ax.set_title(title, fontsize=16, color='white', fontweight='bold', pad=20)

    # Add a subtle confirmation note at the bottom
    fig.text(
        0.5, 0.02, 
        "StrikeBot • Bet Confirmation", 
        ha='center', 
        color='#7CFC00', 
        alpha=0.7,
        fontsize=10,
        fontweight='bold'
    )

    # Save table as temporary image with high quality
    temp_filename = "temp_table_image.png"
    plt.savefig(temp_filename, bbox_inches='tight', dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)

    # Step 2: Load both table image and logo
    table_img = Image.open(temp_filename)
    logo_path = os.path.join(os.path.dirname(__file__), "bet_confirmation.png")  # your uploaded logo
    
    try:
        logo_img = Image.open(logo_path).convert("RGBA")
        
        # Resize logo to 15% of table width
        new_logo_width = int(table_img.width * 0.15)
        aspect_ratio = logo_img.height / logo_img.width
        new_logo_size = (new_logo_width, int(new_logo_width * aspect_ratio))
        logo_img = logo_img.resize(new_logo_size, Image.LANCZOS)

        # Create new image with space for both - using dark background
        spacing = 20
        total_height = table_img.height + logo_img.height + spacing
        new_img = Image.new("RGBA", (table_img.width, total_height), (44, 47, 51, 255))  # Discord dark color
        new_img.paste(table_img, (0, 0))
        new_img.paste(logo_img, ((table_img.width - logo_img.width) // 2, table_img.height + spacing), logo_img)

        # Save final image
        new_img.convert("RGB").save(filename)
    except Exception as e:
        # If logo processing fails, just use the table image
        print(f"Warning: Could not process logo: {e}")
        table_img.convert("RGB").save(filename)
    
    # Clean up temporary file
    os.remove(temp_filename)
    return filename


async def prompt_start_options(channel):
    """Sends welcome/start options."""
    await channel.send("Choose an option to get started:")
    await channel.send("Click a button below:", view=MainMenuView())

def prompt_verify(channel):
    """Sends verification reminder."""
    return channel.send("\u26A0\uFE0F Please verify first using: `verify <username> <password>`")

def is_filtration_question(text):
    try:
        prompt = f"""
You are a strict classifier. Classify the following query ONLY as "yes" if the user is trying to search or filter for existing player prop lines — not placing a bet.

Examples of valid search queries (return "yes"):
- If the query mentions a team (e.g., "Nuggets", "Lakers"), include only players who currently play for that team as of today.
- Use the most up-to-date NBA rosters (current season only). Do NOT include players who have left the team.
- If a player has changed teams, only include them if they currently play for the specified team. (e.g. Kentavious Caldwell Pope used to play for the Nuggets but if someone queries Nuggets, it should return only Nugget player lines )
- show me stephen curry props
- what are the lakers lines?
- get all warriors bets
- denver nuggets lines?
- show all player stats
- lines for anthony edwards?
- Even a name of a player, i.e. stephen curry is an example of a search query
- Even a name of a team, i.e. warriors is an example of a search query


Examples of betting queries (return "no"):
- i want to bet on steph curry over 25.5 points
- add lebron under 22
- place a bet on luka over 1.5 steals for $20
- over 24 points for ja morant

Query:
"{text}"

Reply with only one word: "yes" or "no".
"""
        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        reply = response.choices[0].message.content.strip().lower()
        return reply == "yes"
    except Exception as e:
        print(f"❌ Error in classifier: {e}")
        return False

async def handle_search_mode(user_id, message, channel):
    """Handles filtering logic in search mode."""
    query = message.content.strip().lower()
    
    if query == "exit":
        user_modes[user_id] = None
        await channel.send("✅ Exited search mode.")
        # Show main menu
        await channel.send("Main Menu:", view=MainMenuView())
        return
    
    # Process the search query
    if is_filtration_question(query):
        await channel.send("🔍 Searching lines...")
        filtered_df = get_filtered_rows(query)
        if filtered_df.empty:
            await channel.send("❌ No matching lines found.")
        else:
            image_path = generate_table_image(filtered_df)
            await channel.send(file=discord.File(image_path))
        
        # Add exit button after showing results
        await channel.send("Click the button below to exit:", view=ExitSearchView())
        return
    
    # Search for matching players
    matching_players = df[df["player_name"].str.lower().str.contains(query)]
    if not matching_players.empty:
        # Generate and send player stats image
        player_name = matching_players.iloc[0]["player_name"]
        image_path = generate_player_stat_image(player_name)
        if image_path:
            await channel.send(file=discord.File(image_path))
        else:
            await channel.send(f"Found player {player_name} but no stats are available.")
        
        # Add exit button after showing results
        await channel.send("Click the button below to exit:", view=ExitSearchView())
    else:
        # Try to match teams or stats
        team_matches = df[df["opponent"].str.lower().str.contains(query)]
        stat_matches = df[df["stat_type"].str.lower().str.contains(query)]
        
        if not team_matches.empty:
            image_path = generate_table_image(team_matches.head(15))
            await channel.send(file=discord.File(image_path))
        elif not stat_matches.empty:
            image_path = generate_table_image(stat_matches.head(15))
            await channel.send(file=discord.File(image_path))
        else:
            await channel.send("❗ That doesn't look like a search query. Try a player, team, or stat type.")
        
        # Add exit button after showing results
        await channel.send("Click the button below to exit:", view=ExitSearchView())

# Exit button for search mode
class BettingLinesDropdown(ui.Select):
    def __init__(self, category, page=0):
        self.category = category
        self.page = page
        
        # Get unique options based on the category
        if category == "player":
            # Get all unique player names
            all_players = sorted(df["player_name"].unique())
            # Calculate total pages (25 players per page)
            self.total_pages = (len(all_players) + 24) // 25
            # Get players for current page
            start_idx = page * 25
            end_idx = min(start_idx + 25, len(all_players))
            current_players = all_players[start_idx:end_idx]
            
            options = [discord.SelectOption(label=name, value=name) for name in current_players]
            placeholder = f"Select a player (Page {page+1}/{self.total_pages})..."
            
        elif category == "stat":
            # All stat types (usually not many, so no pagination needed)
            options = [discord.SelectOption(label=stat, value=stat) 
                      for stat in sorted(df["stat_type"].unique())]
            placeholder = "Select a stat type..."
            
        elif category == "opponent":
            # Get all unique opponent teams
            all_teams = sorted(df["opponent"].unique())
            options = [discord.SelectOption(label=team, value=team) for team in all_teams]
            placeholder = "Select an opponent team..."
            
        elif category == "popular":
            # Get most popular options for quick access
            popular_players = df["player_name"].value_counts().head(15).index.tolist()
            popular_stats = df["stat_type"].value_counts().head(10).index.tolist()
            
            options = []
            # Add players with "Player:" prefix
            for player in sorted(popular_players):
                options.append(discord.SelectOption(label=f"Player: {player}", value=f"player:{player}"))
            # Add stats with "Stat:" prefix
            for stat in sorted(popular_stats):
                options.append(discord.SelectOption(label=f"Stat: {stat}", value=f"stat:{stat}"))
            
            placeholder = "Select a popular betting line..."
        
        # Initialize the select menu
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # Get the selected value
        selected_value = self.values[0]
        
        # Parse the selection if it has a category prefix
        if ":" in selected_value:
            category, value = selected_value.split(":", 1)
            if category == "player":
                filtered_df = df[df["player_name"] == value]
            elif category == "stat":
                filtered_df = df[df["stat_type"] == value]
            elif category == "opponent":
                filtered_df = df[df["opponent"] == value]
        else:
            # Direct selection based on the dropdown category
            if self.category == "player":
                # If this is a paginated player dropdown and there are more pages
                if hasattr(self, 'total_pages') and self.page < self.total_pages - 1 and selected_value == "Next Page":
                    # Show next page of players
                    await interaction.response.defer()
                    view = ui.View(timeout=None)
                    view.add_item(BettingLinesDropdown("player", self.page + 1))
                    await interaction.channel.send(f"Players (Page {self.page + 2}/{self.total_pages}):", view=view)
                    return
                filtered_df = df[df["player_name"] == selected_value]
            elif self.category == "stat":
                filtered_df = df[df["stat_type"] == selected_value]
            elif self.category == "opponent":
                filtered_df = df[df["opponent"] == selected_value]
            else:
                # Default case
                filtered_df = df[df["player_name"] == selected_value]
        
        await interaction.response.defer()
        
        # Generate and display the filtered results
        if filtered_df.empty:
            await interaction.channel.send("❌ No matching lines found.")
        else:
            # Add a message showing what was selected
            if ":" in selected_value:
                category, value = selected_value.split(":", 1)
                selection_type = category.capitalize()
                await interaction.channel.send(f"🔍 **Showing lines for {selection_type}: {value}**")
            else:
                selection_type = self.category.capitalize()
                await interaction.channel.send(f"🔍 **Showing lines for {selection_type}: {selected_value}**")
            
            # Show the results in a nicely formatted table
            image_path = generate_table_image(filtered_df)
            await interaction.channel.send(file=discord.File(image_path))
        
        # Show browse options again
        view = BrowseLinesView()
        await interaction.channel.send("Browse more betting lines:", view=view)

class AdvancedSearchModal(ui.Modal, title="Advanced Search"):
    search_query = ui.TextInput(
        label="Search Query", 
        placeholder="Enter player, team, and/or stat (e.g., Steph Curry assists, Lakers, Bucks points)", 
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_query.value
        await interaction.response.send_message(
            f"🔍 Searching for: '{query}'... This may take a moment.", 
            ephemeral=True
        )
        await self.process_advanced_search(interaction, query)
    
    async def process_advanced_search(self, interaction, query):
        # Common stat abbreviations and variations mapping
        stat_mappings = {
            "pts": "points", "point": "points", "scoring": "points",
            "ast": "assists", "assist": "assists", "passing": "assists",
            "reb": "rebounds", "rebound": "rebounds", "boards": "rebounds",
            "blk": "blocks", "block": "blocks",
            "stl": "steals", "steal": "steals",
            "to": "turnovers", "turnover": "turnovers"
        }
        
        # Parse query into components (split by 'and' or commas)
        sub_queries = [q.strip() for q in re.split(r'\s+and\s+|\s*,\s*', query)]
        all_results = []
        result_descriptions = []
        
        for sub_query in sub_queries:
            sub_query_lower = sub_query.lower()
            filtered_df = None
            result_desc = ""
            
            # Process team queries
            team_result = resolve_team_name(sub_query)
            if team_result:
                filtered_df, result_desc = self._process_team_query(
                    team_result, sub_query_lower, stat_mappings
                )
                if filtered_df is not None and not filtered_df.empty:
                    all_results.append(filtered_df)
                    result_descriptions.append(result_desc)
                continue
            
            # Process player and stat queries
            resolved_player = resolve_player_name(sub_query)
            found_stats = self._find_stats_in_query(sub_query_lower, stat_mappings)
            
            if resolved_player and found_stats:
                # Player + stat(s) query
                filtered_df = self._filter_by_player_and_stats(resolved_player, found_stats)
                if not filtered_df.empty:
                    all_results.append(filtered_df)
                    result_descriptions.append(f"{resolved_player} {', '.join(found_stats)}")
            
            elif resolved_player:
                # Player-only query
                filtered_df = df[df["player_name"] == resolved_player]
                if not filtered_df.empty:
                    all_results.append(filtered_df)
                    result_descriptions.append(f"{resolved_player}")
            
            elif found_stats:
                # Stat-only query
                filtered_df = self._filter_by_stats(found_stats)
                if not filtered_df.empty:
                    all_results.append(filtered_df)
                    result_descriptions.append(f"{', '.join(found_stats)}")
            
            else:
                # Fallback to GPT-based filtering
                try:
                    filtered_df = get_filtered_rows(sub_query)
                    if not filtered_df.empty:
                        all_results.append(filtered_df)
                        result_descriptions.append(f"{sub_query}")
                except Exception as e:
                    print(f"Error using get_filtered_rows for '{sub_query}': {e}")
        
        # Display results
        if not all_results:
            await interaction.followup.send(
                f"No betting lines found matching '{query}'. Try being more specific with player names, teams, or stat types.", 
                ephemeral=True
            )
            return
        
        # Combine results and display
        combined_df = pd.concat(all_results).drop_duplicates()
        result_summary = " and ".join(result_descriptions)
        
        await interaction.channel.send(f"🔍 **Showing lines for: {result_summary}**")
        image_path = generate_table_image(combined_df)
        await interaction.channel.send(file=discord.File(image_path))
        await interaction.channel.send("Browse more betting lines:", view=BrowseLinesView())
    
    def _find_stats_in_query(self, query_text, stat_mappings):
        """Extract stat types from query text."""
        all_stats = [stat.lower() for stat in df["stat_type"].unique()]
        found_stats = [stat for stat in all_stats if stat in query_text]
        
        # Check for common variations and abbreviations
        for term in query_text.split():
            if term in stat_mappings and stat_mappings[term] not in found_stats:
                found_stats.append(stat_mappings[term])
                
        return found_stats
    
    def _process_team_query(self, team_result, query_text, stat_mappings):
        """Process a team-based query."""
        team_code = team_result["team"]
        team_players = team_result["players"]
        
        if not team_players:
            return None, ""
        
        # Find stats in the query
        found_stats = self._find_stats_in_query(query_text, stat_mappings)
        
        # Create player filters
        player_filters = [df["player_name"] == player for player in team_players]
        combined_player_filter = player_filters[0]
        for f in player_filters[1:]:
            combined_player_filter = combined_player_filter | f
        
        # Apply stat filters if any
        if found_stats:
            stat_filters = [df["stat_type"].str.lower() == stat.lower() for stat in found_stats]
            combined_stat_filter = stat_filters[0]
            for f in stat_filters[1:]:
                combined_stat_filter = combined_stat_filter | f
            
            filtered_df = df[combined_player_filter & combined_stat_filter]
            result_desc = f"{team_code} {', '.join(found_stats)}"
        else:
            filtered_df = df[combined_player_filter]
            result_desc = f"{team_code} players"
        
        return filtered_df, result_desc
    
    def _filter_by_player_and_stats(self, player_name, stats):
        """Filter betting lines by player and stats."""
        player_filter = df["player_name"] == player_name
        stat_filters = [df["stat_type"].str.lower() == stat.lower() for stat in stats]
        
        combined_stat_filter = stat_filters[0]
        for f in stat_filters[1:]:
            combined_stat_filter = combined_stat_filter | f
        
        return df[player_filter & combined_stat_filter]
    
    def _filter_by_stats(self, stats):
        """Filter betting lines by stats only."""
        stat_filters = [df["stat_type"].str.lower() == stat.lower() for stat in stats]
        combined_filter = stat_filters[0]
        
        for f in stat_filters[1:]:
            combined_filter = combined_filter | f
            
        return df[combined_filter]

class PlayerSearchModal(ui.Modal, title="Search for a Player"):
    search_query = ui.TextInput(label="Player Name", placeholder="Enter player name (e.g., Steph Curry)", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_query.value
        
        # Try to resolve the player name using the existing function
        resolved_player = resolve_player_name(query)
        
        if resolved_player:
            # If we got a direct match from the resolver
            filtered_df = df[df["player_name"] == resolved_player]
            await interaction.response.defer()
            
            # Show the results
            await interaction.channel.send(f"🔍 **Showing lines for Player: {resolved_player}**")
            image_path = generate_table_image(filtered_df)
            await interaction.channel.send(file=discord.File(image_path))
            
            # Show browse options again
            browse_view = BrowseLinesView()
            await interaction.channel.send("Browse more betting lines:", view=browse_view)
            return
        
        # If resolver didn't find a match, fall back to manual search
        query_lower = query.lower()
        all_players = df["player_name"].unique()
        
        # Sort matches by relevance (exact matches first, then starts with, then contains)
        exact_matches = [p for p in all_players if p.lower() == query_lower]
        starts_with = [p for p in all_players if p.lower().startswith(query_lower) and p.lower() != query_lower]
        contains = [p for p in all_players if query_lower in p.lower() and not p.lower().startswith(query_lower) and p.lower() != query_lower]
        
        matching_players = exact_matches + starts_with + contains
        
        if not matching_players:
            await interaction.response.send_message(f"No players found matching '{query}'", ephemeral=True)
            return
        
        # Create a dropdown with the matching players
        view = ui.View(timeout=None)
        
        # If we have more than 25 matches, we need to paginate
        if len(matching_players) > 25:
            # Just show the top 25 most relevant matches
            options = [discord.SelectOption(label=player, value=player) for player in matching_players[:25]]
            await interaction.response.send_message(f"Found {len(matching_players)} players matching '{query}'. Showing top 25 matches:", ephemeral=True)
        else:
            options = [discord.SelectOption(label=player, value=player) for player in matching_players]
            await interaction.response.send_message(f"Found {len(matching_players)} players matching '{query}':", ephemeral=True)
        
        # Create a custom select with the search results
        select = ui.Select(placeholder="Select a player from search results", options=options)
        
        async def select_callback(select_interaction):
            selected_player = select_interaction.data["values"][0]
            
            # Get the betting lines for this player
            filtered_df = df[df["player_name"] == selected_player]
            
            await select_interaction.response.defer()
            
            # Show the results
            await interaction.channel.send(f"🔍 **Showing lines for Player: {selected_player}**")
            image_path = generate_table_image(filtered_df)
            await interaction.channel.send(file=discord.File(image_path))
            
            # Show browse options again
            browse_view = BrowseLinesView()
            await interaction.channel.send("Browse more betting lines:", view=browse_view)
        
        select.callback = select_callback
        view.add_item(select)
        await interaction.channel.send("Select a player from the search results:", view=view)

class StatSearchModal(ui.Modal, title="Search for a Stat Type"):
    search_query = ui.TextInput(label="Stat Type", placeholder="Enter stat type (e.g., points, assists)", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_query.value.lower()
        
        # Map common stat abbreviations and variations
        stat_mappings = {
            "pts": "points", "point": "points", "scoring": "points",
            "ast": "assists", "assist": "assists", "passing": "assists",
            "reb": "rebounds", "rebound": "rebounds", "boards": "rebounds",
            "blk": "blocks", "block": "blocks",
            "stl": "steals", "steal": "steals",
            "to": "turnovers", "turnover": "turnovers"
        }
        
        # Check if the query directly matches a known stat type or abbreviation
        if query in stat_mappings:
            query = stat_mappings[query]
        
        # Search for stat types that match the query
        all_stats = df["stat_type"].unique()
        
        # Sort matches by relevance (exact matches first, then starts with, then contains)
        exact_matches = [s for s in all_stats if s.lower() == query]
        starts_with = [s for s in all_stats if s.lower().startswith(query) and s.lower() != query]
        contains = [s for s in all_stats if query in s.lower() and not s.lower().startswith(query) and s.lower() != query]
        
        matching_stats = exact_matches + starts_with + contains
        
        # If we have an exact match or only one match, use it directly
        if exact_matches or len(matching_stats) == 1:
            selected_stat = exact_matches[0] if exact_matches else matching_stats[0]
            
            # Get the betting lines for this stat type
            filtered_df = df[df["stat_type"].str.lower() == selected_stat.lower()]
            
            await interaction.response.defer()
            
            # Show the results directly
            await interaction.channel.send(f"🔍 **Showing lines for Stat Type: {selected_stat}**")
            image_path = generate_table_image(filtered_df)
            await interaction.channel.send(file=discord.File(image_path))
            
            # Show browse options again
            browse_view = BrowseLinesView()
            await interaction.channel.send("Browse more betting lines:", view=browse_view)
            return
        
        # If we have multiple matches but no exact match, show a dropdown
        if matching_stats:
            # Create a dropdown with the matching stat types
            view = ui.View(timeout=None)
            
            options = [discord.SelectOption(label=stat, value=stat) for stat in matching_stats]
            await interaction.response.send_message(f"Found {len(matching_stats)} stat types matching '{self.search_query.value}':", ephemeral=True)
            
            # Create a custom select with the search results
            select = ui.Select(placeholder="Select a stat type from search results", options=options)
            
            async def select_callback(select_interaction):
                selected_stat = select_interaction.data["values"][0]
                
                # Get the betting lines for this stat type
                filtered_df = df[df["stat_type"] == selected_stat]
                
                await select_interaction.response.defer()
                
                # Show the results
                await interaction.channel.send(f"🔍 **Showing lines for Stat Type: {selected_stat}**")
                image_path = generate_table_image(filtered_df)
                await interaction.channel.send(file=discord.File(image_path))
                
                # Show browse options again
                browse_view = BrowseLinesView()
                await interaction.channel.send("Browse more betting lines:", view=browse_view)
            
            select.callback = select_callback
            view.add_item(select)
            await interaction.channel.send("Select a stat type from the search results:", view=view)
        else:
            await interaction.response.send_message(f"No stat types found matching '{self.search_query.value}'", ephemeral=True)

class BrowseLinesView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Add dropdown for popular options
        self.add_item(BettingLinesDropdown("popular"))
    
    @ui.button(label="Advanced Search", style=ButtonStyle.primary, row=1)
    async def advanced_search_button(self, interaction: discord.Interaction, button: ui.Button):
        # Show a modal for advanced search (player + stat combined)
        modal = AdvancedSearchModal()
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Search Player", style=ButtonStyle.secondary, row=1)
    async def search_player_button(self, interaction: discord.Interaction, button: ui.Button):
        # Show a modal for player search
        modal = PlayerSearchModal()
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Search Stat", style=ButtonStyle.secondary, row=1)
    async def search_stat_button(self, interaction: discord.Interaction, button: ui.Button):
        # Show a modal for stat search
        modal = StatSearchModal()
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Exit", style=ButtonStyle.danger, row=2)
    async def exit_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = str(interaction.user.id)
        user_modes[user_id] = None
        
        await interaction.response.defer()
        await interaction.channel.send("✅ Exited search mode.")
        
        # Show main menu
        await interaction.channel.send("Main Menu:", view=MainMenuView())

class ExitSearchView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Browse All Lines", style=ButtonStyle.primary, custom_id="browse_lines_button")
    async def browse_lines_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        view = BrowseLinesView()
        await interaction.channel.send("Browse betting lines by category:", view=view)
    
    @ui.button(label="Exit Search", style=ButtonStyle.danger, custom_id="exit_search_button")
    async def exit_search_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = str(interaction.user.id)
        user_modes[user_id] = None
        
        # Show exit message and main menu
        await interaction.channel.send("✅ Exited search mode.")
        await interaction.channel.send("Main Menu:", view=MainMenuView())

# Main menu view with buttons for search and place bets
class MainMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Search Betting Lines", style=ButtonStyle.primary, custom_id="search_button")
    async def search_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = str(interaction.user.id)
        
        # Check if user is verified
        if user_id not in verified_users:
            await interaction.response.send_message("You need to verify your account first. Type `!verify` to start.", ephemeral=True)
            return
        
        # Set user mode to search
        user_modes[user_id] = "search"
        await interaction.response.defer()
        
        # Show the browse lines view for a more organized search experience
        view = BrowseLinesView()
        await interaction.channel.send(
            "🔎 **Search Betting Lines**\n"
            "Browse all available betting lines by category or search by text."
        )
        await interaction.channel.send("Select an option below:", view=view)
    
    @ui.button(label="Place Bets", style=ButtonStyle.success, custom_id="place_bets_button")
    async def place_bets_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = str(interaction.user.id)
        
        # Check if user is verified
        if user_id not in verified_users:
            await interaction.response.send_message("You need to verify your account first. Type `!verify` to start.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Set user mode to nlp_bet
        user_modes[user_id] = "nlp_bet"
        user_nlp_bet_state[user_id] = {"stage": "initial"}
        
        # Show the bet form
        view = NaturalBetView()
        await interaction.channel.send(
            "🎮 **Natural Language Betting Mode**\n"
            "You can now place bets using natural language! For example:\n"
            "• `LeBron over 25.5 points`\n"
            "• `Curry under 7 assists and Giannis over 30 points`\n"
            "\nOr click the button below to open the bet form:",
            view=view
        )

# Login button UI class
class LoginView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    

    @ui.button(label="Login", style=ButtonStyle.primary, custom_id="login_button")
    async def login_button(self, interaction: discord.Interaction, button: ui.Button):
        # Create a modal for login
        await interaction.response.send_modal(LoginModal())
        
class NaturalBetView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Place a Bet", style=ButtonStyle.primary, custom_id="bet_button")
    async def bet_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BetModal())
    
    @ui.button(label="View Cart", style=ButtonStyle.success, custom_id="view_cart_button")
    async def view_cart_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = str(interaction.user.id)
        user_cart = user_carts.get(user_id, [])
        
        await interaction.response.defer()
        
        if not user_cart:
            await interaction.channel.send("🛒 Your cart is empty. Place a bet to add items to your cart.")
            return
        
        # Display the cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, "Pending", filename="cart_preview.png")
        await interaction.channel.send(f"🛒 **Your Cart** - {len(user_cart)} bets", file=discord.File(cart_image))
        
        # Show cart management options
        view = CartManagementView(user_id)
        await interaction.channel.send("Cart Options:", view=view)
    
    @ui.button(label="Exit Betting Mode", style=ButtonStyle.danger, custom_id="exit_betting_button")
    async def exit_betting_button(self, interaction: discord.Interaction, button: ui.Button):
        user_id = str(interaction.user.id)
        
        # Exit betting mode
        user_modes[user_id] = None
        if user_id in user_nlp_bet_state:
            del user_nlp_bet_state[user_id]
        
        await interaction.response.defer()
        await interaction.channel.send("✅ Exited betting mode.")
        
        # Show main menu
        await interaction.channel.send("Main Menu:", view=MainMenuView())

# Combined betting and cart view
class BettingWithCartView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="Place a Bet", style=ButtonStyle.primary, custom_id="place_bet_with_cart")
    async def place_bet_with_cart(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This option is for someone else.", ephemeral=True)
            return
        
        await interaction.response.send_modal(BetModal())
    
    @ui.button(label="View Cart", style=ButtonStyle.success, custom_id="view_cart_combined")
    async def view_cart_combined(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        user_cart = user_carts.get(self.user_id, [])
        
        await interaction.response.defer()
        
        if not user_cart:
            await interaction.channel.send("🛒 Your cart is empty. Place a bet to add items to your cart.")
            return
        
        # Display the cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, "Pending", filename="cart_preview.png")
        await interaction.channel.send(f"🛒 **Your Cart** - {len(user_cart)} bets", file=discord.File(cart_image))
        
        # Show cart management options
        view = CartManagementView(self.user_id)
        await interaction.channel.send("Cart Options:", view=view)
    
    @ui.button(label="Exit Betting Mode", style=ButtonStyle.danger, custom_id="exit_betting_combined")
    async def exit_betting_combined(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This option is for someone else.", ephemeral=True)
            return
        
        # Exit betting mode
        user_modes[self.user_id] = None
        if self.user_id in user_nlp_bet_state:
            del user_nlp_bet_state[self.user_id]
        
        await interaction.response.defer()
        await interaction.channel.send("✅ Exited betting mode.")
        
        # Show main menu
        await interaction.channel.send("Main Menu:", view=MainMenuView())

# Cart management view
class CartManagementView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="Confirm Cart", style=ButtonStyle.success, custom_id="confirm_cart_button")
    async def confirm_cart_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        user_cart = user_carts.get(self.user_id, [])
        if not user_cart:
            await interaction.response.send_message("🛒 Your cart is empty. Add bets first.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Process the cart without asking for bet amount
        await process_bet_confirmation({"players": []}, self.user_id, interaction.channel)
    
    @ui.button(label="Clear Cart", style=ButtonStyle.danger, custom_id="clear_cart_button")
    async def clear_cart_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        # Clear the cart
        user_carts[self.user_id] = []
        
        await interaction.response.defer()
        await interaction.channel.send("🚮 Cart cleared! Start fresh with new bets.")
        
        # Show the bet form again with cart options
        view = BettingWithCartView(self.user_id)
        await interaction.channel.send("Click a button below:", view=view)
    
    @ui.button(label="Add Another Bet", style=ButtonStyle.primary, custom_id="add_another_from_cart")
    async def add_another_from_cart(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Show the bet form with cart options
        view = BettingWithCartView(self.user_id)
        await interaction.channel.send("Click a button below:", view=view)
    
    @ui.button(label="Return to Main Menu", style=ButtonStyle.secondary, custom_id="cart_to_menu")
    async def cart_to_menu(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This option is for someone else.", ephemeral=True)
            return
        
        # Exit betting mode
        user_modes[self.user_id] = None
        
        await interaction.response.defer()
        await interaction.channel.send("Main Menu:", view=MainMenuView())

# Bet amount entry view with clear labels
# BetAmountView class has been removed as requested

# Follow-up question button UI with specific labels
class FollowUpView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        
        # Get the current state to determine button label
        state = user_nlp_bet_state.get(user_id, {})
        current_field = state.get("current_field")
        
        # Set appropriate button label based on what we're asking for
        if current_field == "name":
            self.button_label = "Enter Player Name"
        elif current_field == "stat_type":
            self.button_label = "Enter Stat Type"
        elif current_field == "line_value":
            self.button_label = "Enter Line Value"
        elif current_field == "bet_type":
            self.button_label = "Select Over/Under"
        elif state.get("asking_for_entry_fee", False):
            self.button_label = "Enter Bet Amount"
        else:
            self.button_label = "Continue"
    
    @ui.button(label="Continue", style=ButtonStyle.primary, custom_id="continue_bet_button")
    async def continue_bet_button(self, interaction: discord.Interaction, button: ui.Button):
        # Update the button label to be more specific
        button.label = self.button_label
        
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        # Get the current state
        state = user_nlp_bet_state.get(self.user_id, {})
        
        # Show the appropriate modal based on the current field
        current_field = state.get("current_field")
        
        if current_field == "name":
            await interaction.response.send_modal(PlayerNameModal(self.user_id))
        elif current_field == "stat_type":
            await interaction.response.send_modal(StatTypeModal(self.user_id))
        elif current_field == "line_value":
            await interaction.response.send_modal(LineValueModal(self.user_id))
        elif current_field == "bet_type":
            await interaction.response.send_modal(BetTypeModal(self.user_id))
        elif state.get("asking_for_entry_fee", False):
            await interaction.response.send_modal(EntryFeeModal(self.user_id))
        else:
            # Default to bet modal
            await interaction.response.send_modal(BetModal())
    
    @ui.button(label="Cancel", style=ButtonStyle.danger, custom_id="cancel_follow_up")
    async def cancel_follow_up(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        # Clear the current field to cancel this specific follow-up
        state = user_nlp_bet_state.get(self.user_id, {})
        if "current_field" in state:
            del state["current_field"]
        state["waiting_for_input"] = False
        user_nlp_bet_state[self.user_id] = state
        
        await interaction.response.defer()
        await interaction.channel.send("❌ Input canceled. Returning to betting menu.")
        
        # Show the bet form again
        view = NaturalBetView()
        await interaction.channel.send("Click the button below to place a bet:", view=view)

# Player name modal
class PlayerNameModal(ui.Modal, title="Player Selection"):
    player_name = ui.TextInput(
        label="Player Name", 
        placeholder="Enter NBA player name (e.g., LeBron James, Curry)",
        required=True
    )
    
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id
        channel = interaction.channel
        input_value = str(self.player_name)
        
        # Update state
        state = user_nlp_bet_state.get(user_id, {})
        state["last_input"] = input_value
        state["waiting_for_input"] = False
        user_nlp_bet_state[user_id] = state
        
        await interaction.response.defer()
        
        # Process the input
        await process_bet_input("", user_id, channel)

# Stat type modal
class StatTypeModal(ui.Modal, title="Stat Type Selection"):
    stat_type = ui.TextInput(
        label="Stat Type", 
        placeholder="Enter stat type (e.g., points, rebounds, assists)",
        required=True
    )
    
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id
        channel = interaction.channel
        input_value = str(self.stat_type)
        
        # Update state
        state = user_nlp_bet_state.get(user_id, {})
        state["last_input"] = input_value
        state["waiting_for_input"] = False
        user_nlp_bet_state[user_id] = state
        
        await interaction.response.defer()
        
        # Process the input
        await process_bet_input("", user_id, channel)

# Line value modal
class LineValueModal(ui.Modal, title="Line Value Selection"):
    line_value = ui.TextInput(
        label="Line Value", 
        placeholder="Enter the line value (e.g., 25.5)",
        required=True
    )
    
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id
        channel = interaction.channel
        input_value = str(self.line_value)
        
        # Update state
        state = user_nlp_bet_state.get(user_id, {})
        state["last_input"] = input_value
        state["waiting_for_input"] = False
        user_nlp_bet_state[user_id] = state
        
        await interaction.response.defer()
        
        # Process the input
        await process_bet_input("", user_id, channel)

# Bet type modal
class BetTypeModal(ui.Modal, title="Bet Type Selection"):
    bet_type = ui.TextInput(
        label="Bet Type", 
        placeholder="Type either 'over' or 'under'",
        required=True
    )
    
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id
        channel = interaction.channel
        input_value = str(self.bet_type).lower().strip()
        
        # Update state
        state = user_nlp_bet_state.get(user_id, {})
        state["last_input"] = input_value
        state["waiting_for_input"] = False
        
        # Debug log
        print(f"BetTypeModal - User ID: {user_id}, Input: {input_value}, State: {state}")
        
        # Make sure the state is saved
        user_nlp_bet_state[user_id] = state
        
        await interaction.response.defer()
        
        # Process the input
        await process_bet_input("", user_id, channel)

# Entry fee modal
# Entry fee modal has been removed as requested
        
# Bet modal UI class with improved instructions
class BetModal(ui.Modal, title="Place Your Bet"):
    bet_text = ui.TextInput(
        label="Describe your bet", 
        placeholder="Example: $20 on LeBron over 25.5 points",
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        channel = interaction.channel
        bet_input = str(self.bet_text)
        
        await interaction.response.defer()
        
        # Show a processing message
        await channel.send("🔍 Processing your bet... Please wait.")
        
        # Process the natural language bet
        await process_bet_input(bet_input, user_id, channel)

# Login modal UI class
class LoginModal(ui.Modal, title="StrikeBot Login"):
    username = ui.TextInput(label="Username", placeholder="Enter your username", required=True)
    password = ui.TextInput(label="Password", placeholder="Enter your password", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        channel = interaction.channel
        username = str(self.username)
        password = str(self.password)

        await interaction.response.defer(ephemeral=True)

        try:
            res = requests.post("http://localhost:5050/login", json={
                "username": username,
                "password": password
            })
            data = res.json()
            if data.get("success"):
                verified_users.add(user_id)
                await interaction.followup.send("✅ Login successful! Welcome to StrikeBot!", ephemeral=True)
                await prompt_start_options(channel)
            else:
                await interaction.followup.send(f"❌ Login failed: {data.get('reason', 'Unknown error')}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error during login: {e}", ephemeral=True)

# Function to send verification message with login button
async def send_verification_message(channel):
    view = LoginView()
    await channel.send(
        "👋 Welcome to **StrikeBot** — your Discord companion for placing NBA prop bets!\n"
        "Please click the button below to login:", 
        view=view
    )

# Legacy verification handler (for backward compatibility)
async def handle_verification(message):
    user_id = str(message.author.id)
    channel = message.channel

    global login_notified_users, verified_users
    text = message.content.strip().lower()
    parts = text.split()
    if len(parts) != 3:
        await channel.send("\u274C Usage: `verify <username> <password>`")
        return
    _, username, password = parts

    if user_id not in login_notified_users:
        login_notified_users.add(user_id)
        await channel.send("🔐 Attempting login...")

        try:
            res = requests.post("http://localhost:5050/login", json={
                "username": username,
                "password": password
            })
            data = res.json()
            if data.get("success"):
                verified_users.add(user_id)
                await channel.send("\u2705 Login successful! Welcome to StrikeBot!")
                await prompt_start_options(channel)
            else:
                await channel.send(f"\u274C Login failed: {data.get('reason', 'Unknown error')}")
        except Exception as e:
            await channel.send(f"\u274C Error during login: {e}")


# --- Utilities ---
def extract_bet_info(user_input):
    prompt = f"""
You are an API that extracts structured bet information from user input. You MUST return a valid JSON object only — no explanation, no commentary.

Example Input:
"$20 on LeBron over 25.5 points and Curry under 3.5 turnovers"

Expected Output:
{{
  "entry_fee": 20,
  "players": [
    {{
      "name": "LeBron James",
      "bet_type": "over",
      "line_value": 25.5,
      "stat_type": "points"
    }},
    {{
      "name": "Stephen Curry",
      "bet_type": "under",
      "line_value": 3.5,
      "stat_type": "turnovers"
    }}
  ]
}}

For incomplete inputs, mark missing fields with null. For example:
{{
  "entry_fee": null,  # If no amount specified
  "players": [
    {{
      "name": "LeBron James",
      "bet_type": null,  # If over/under not specified
      "line_value": null,  # If line value not specified
      "stat_type": "points"
    }}
  ]
}}

User Input:
"{user_input}"

Now respond ONLY with a valid JSON object in that format.
"""

    response = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a JSON-only API. Never include explanations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
    )
    
    # Try parsing the response
    response_text = response.choices[0].message.content.strip()
    
    # Remove markdown formatting if present
    if response_text.startswith("```json") and response_text.endswith("```"):
        response_text = response_text[7:-3].strip()
    elif response_text.startswith("```") and response_text.endswith("```"):
        response_text = response_text[3:-3].strip()

    try:
        # Parse the JSON to validate it
        parsed_data = json.loads(response_text)
        
        # Validate player names against the database
        if "players" in parsed_data and parsed_data["players"]:
            valid_players = []
            invalid_players = []
            
            # Get all player names from the database
            all_player_names = df["player_name"].unique()
            all_player_names_lower = [name.lower() for name in all_player_names]
            
            for player in parsed_data["players"]:
                if player.get("name"):
                    player_name = player["name"]
                    
                    # Check if player exists in the database (case-insensitive)
                    if player_name.lower() in all_player_names_lower:
                        # Find the exact case-matching name from the database
                        for db_name in all_player_names:
                            if db_name.lower() == player_name.lower():
                                player["name"] = db_name  # Use the exact name from the database
                                valid_players.append(player)
                                break
                    else:
                        # Player not found in database
                        invalid_players.append(player_name)
            
            # Update the parsed data with validation results
            if invalid_players:
                parsed_data["invalid_players"] = invalid_players
            parsed_data["players"] = valid_players
        
        return parsed_data
    except json.JSONDecodeError:
        # If parsing fails, return None
        return None

def get_filtered_rows(user_query):
    try:
        prompt = f"""
You are a smart NBA betting assistant. Given a user query and a list of betting lines, return only the entries that match the filters based on CURRENT NBA knowledge.

⚠️ STRICT RULES:
1. If the query mentions a team (e.g., "Nuggets", "Lakers"), include only players who currently play for that team.
2. Use current NBA rosters (as of today).
3. If the query includes **multiple filters**, like teams and players or multiple stat types, return the **union** of all matching conditions.
4. Normalize stat types (e.g., "rebound" → "rebounds", "assist" → "assists").
5. If stat type or team is implied but not explicitly named, infer reasonably.
6. Output must be a **valid JSON array**. No explanations, no markdown, no extra text.
7. If nothing matches, return [].

Examples of filterable properties:
- Player name
- Team name (must be filtered to current roster)
- Stat type (rebounds, points, assists, etc.)

User Query:
{user_query}

Betting Events (list of dicts):
{df[['player_name', 'stat_type', 'line_value', 'opponent']].to_dict(orient='records')}

Your response: JSON array of matched betting events (dicts). Nothing else.
"""

        response = client_ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text[3:-3].strip()
        if not response_text.startswith("["):
            raise ValueError("GPT response did not return JSON list")

        return pd.DataFrame(json.loads(response_text))

    except Exception as e:
        print("❌ GPT filter error:", e)
        return pd.DataFrame([])



def generate_table_image(filtered_df, filename="lines_preview.png"):
    # Set the style for the plot
    plt.style.use('ggplot')
    
    # Create figure with a dark background
    fig, ax = plt.subplots(figsize=(12, min(0.6 * len(filtered_df) + 1.5, 25)))
    fig.patch.set_facecolor('#2C2F33')  # Discord-like dark background
    ax.set_facecolor('#2C2F33')
    ax.axis('off')
    
    # Add a title with NBA-themed styling
    ax.set_title('NBA Prop Betting Lines', fontsize=16, color='white', fontweight='bold', pad=20)
    
    # Prepare data for the table
    column_titles = ["Player", "Stat Type", "Line", "Opponent"]
    table_data = filtered_df[["player_name", "stat_type", "line_value", "opponent"]].values.tolist()
    
    # Create the table with custom styling
    table = ax.table(
        cellText=table_data, 
        colLabels=column_titles, 
        loc='center', 
        cellLoc='center',
        colWidths=[0.3, 0.25, 0.15, 0.3]  # Adjust column widths for better proportions
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)
    
    # Style header row (team colors - using Lakers purple and gold as inspiration)
    header_color = '#552583'  # Lakers purple
    header_text_color = '#FDB927'  # Lakers gold
    
    for col in range(len(column_titles)):
        cell = table[0, col]
        cell.set_facecolor(header_color)
        cell.set_text_props(color=header_text_color, weight='bold')
        cell.set_edgecolor('white')
    
    # Style data rows with alternating colors for better readability
    for row in range(1, len(table_data) + 1):
        row_color = '#36393F' if row % 2 == 0 else '#40444B'  # Discord-like alternating row colors
        
        for col in range(len(column_titles)):
            cell = table[row, col]
            cell.set_facecolor(row_color)
            cell.set_text_props(color='white')
            cell.set_edgecolor('#23272A')  # Darker border color
    
    # Add a subtle border around the entire table
    for pos, cell in table._cells.items():
        cell.set_linewidth(0.5)
    
    # Add a subtle NBA-themed watermark/logo hint at the bottom
    fig.text(
        0.5, 0.02, 
        "StrikeBot NBA Props", 
        ha='center', 
        color='#FDB927', 
        alpha=0.7,
        fontsize=10,
        fontweight='bold'
    )
    
    # Save with high quality
    plt.savefig(filename, bbox_inches='tight', dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    return filename







def generate_bets_payload(user_id, entry_fee, user_cart):
    # Extract bet details based on your specified format
    bets = []

    for bet in user_cart:
        player_name = bet.get("player_name")
        stat_type = bet.get("stat_type")
        line_value = bet.get("line_value")

        # Lookup event_id from the CSV using player name, stat type, and line value
        matching_event = df[(df["player_name"] == player_name) &
                                           (df["stat_type"].str.lower() == stat_type.lower()) &
                                           (df["line_value"] == line_value)]

        event_id = matching_event.iloc[0]["event_id"] if not matching_event.empty else None

        bets.append({
            "event_id": event_id,
            "bet_side": bet.get("bet_type"),
            "line_value": line_value,

        })

    # Build the final payload dictionary with the provided entry_fee
    payload = {
        "user_id": user_id,
        "bets": bets,
        "entry_fee": entry_fee  # Use the provided entry_fee
    }

    return payload



    



# --- Events ---
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    for guild in client.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    # Send verification message with login button
                    await send_verification_message(channel)
                    break  # Only send to one channel per guild
                except Exception as e:
                    print(f"❌ Could not send welcome message in {channel.name}: {e}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_id = str(message.author.id)
    text = message.content.strip().lower()

    if user_id not in verified_users:
        if text.startswith("verify"):
            # Support legacy verification method
            await handle_verification(message)
        else:
            # Send a reminder with the login button
            view = LoginView()
            await message.channel.send("⚠️ Please login first to use StrikeBot:", view=view)
        return

    if text == "start" or text == "menu" or text == "main menu":
        await show_main_menu(message, user_id)
        return

    if text == "search":
        user_modes[user_id] = "search"
        await message.channel.send(
            "🔎 Enter a team name, player, or stat type to view matching lines. Type `exit` to leave search mode and place bets."
        )
        return

    if text == "exit":
        current_mode = user_modes.get(user_id)
        user_modes[user_id] = None
        guided_bet_state[user_id] = {}
    
        if current_mode == "search":
            await message.channel.send("✅ Exited search mode.")
            # Show main menu
            await message.channel.send("Main Menu:", view=MainMenuView())
        elif current_mode == "bet":
            await message.channel.send("✅ Exited betting mode.")
            # Show main menu
            await message.channel.send("Main Menu:", view=MainMenuView())
        else:
            await message.channel.send("ℹ️ You're not in any active mode.")
            # Show main menu
            await message.channel.send("Main Menu:", view=MainMenuView())
        return


    if text == "place bets":
        # Show the natural language bet input UI instead of the guided flow
        user_modes[user_id] = "nlp_bet"
        user_nlp_bet_state[user_id] = {"stage": "initial"}
        view = NaturalBetView()
        await message.channel.send(
            "🎮 **Natural Language Betting Mode**\n"
            "You can now place bets using natural language! For example:\n"
            "• `LeBron over 25.5 points`\n"
            "• `Curry under 7 assists and Giannis over 30 points`\n"
            "\nOr click the button below to open the bet form:",
            view=view
        )
        return
        
    if text == "view cart" or text == "cart":
        # Show the current bet cart
        user_cart = user_carts.get(user_id, [])
        if not user_cart:
            await message.channel.send("🛒 Your cart is empty. Type `place bets` to add bets.")
            return
            
        # Display the cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, "Pending", filename="cart_preview.png")
        await message.channel.send(f"🛒 **Your Cart** - {len(user_cart)} bets", file=discord.File(cart_image))
        
        # Show cart options
        await message.channel.send("Type `confirm cart` to set your wager and place these bets, or `clear cart` to start over.")
        return
        
    if text == "clear cart":
        # Clear the user's cart
        user_carts[user_id] = []
        await message.channel.send("🚮 Cart cleared! Type `place bets` to start over.")
        return
        
    if text == "confirm cart":
        # Confirm the cart and ask for entry fee
        user_cart = user_carts.get(user_id, [])
        if not user_cart:
            await message.channel.send("🛒 Your cart is empty. Type `place bets` to add bets.")
            return
            
        # Set up state for entry fee
        user_nlp_bet_state[user_id] = {
            "stage": "cart_confirmation",
            "waiting_for_input": True,
            "asking_for_entry_fee": True,
            "current_field": None
        }
        
        # Skip asking for entry fee and go straight to bet processing
        await process_bet_input("", user_id, message.channel)
        return

    if user_modes.get(user_id) == "search":
        await handle_search_query(message, user_id)
        return

    # Handle NLP bet mode
    if user_modes.get(user_id) == "nlp_bet":
        await process_nlp_bet(message, user_id, message.channel)
        return
        
    if user_modes.get(user_id) != "bet":
        await message.channel.send("👋 Type `start` to begin.")
        return

    await handle_guided_bet(message, user_id, message.channel)


# Process natural language bets
async def process_nlp_bet(message, user_id, channel):
    # Handle exit command
    if message.content.strip().lower() == "exit":
        user_modes[user_id] = None
        if user_id in user_nlp_bet_state:
            del user_nlp_bet_state[user_id]
        await channel.send("✅ Exited betting mode.")
        # Show main menu
        await channel.send("Main Menu:", view=MainMenuView())
        return
    
    # Get current state
    state = user_nlp_bet_state.get(user_id, {})
    
    # If we're in the middle of collecting specific information, update the state with the user's response
    if state.get("waiting_for_input") and state.get("current_field"):
        state["last_input"] = message.content.strip()
        state["waiting_for_input"] = False
        await process_bet_input("", user_id, channel)
        return
        
    # Process as a new bet input
    await process_bet_input(message.content, user_id, channel)

async def process_bet_input(bet_input, user_id, channel):
    print(f"\n==== PROCESS BET INPUT ====\nUser ID: {user_id}\nInput: {bet_input}")
    
    # Get or initialize the user's state
    state = user_nlp_bet_state.setdefault(user_id, {
        "stage": "initial", 
        "current_player_index": 0,
        "processing_complete": False,
        "bet_data": None
    })
    
    print(f"Initial state: {state}")
    
    # Check if we're in the special flow after Add Another Bet was clicked
    if state.get("waiting_for_nlp_input", False) and bet_input:
        # User has provided a bet after clicking Add Another Bet
        bet_data = extract_bet_info(bet_input)
        
        if bet_data and "players" in bet_data and bet_data["players"]:
            # Reset the state for processing this new bet
            state = {
                "stage": "processing", 
                "bet_data": bet_data, 
                "current_player_index": 0, 
                "processing_complete": False,
                "last_input": bet_input,
                "waiting_for_input": False,
                "current_field": None
            }
            user_nlp_bet_state[user_id] = state
            
            # Continue with normal processing below
        else:
            # Handle invalid bet input
            if not bet_data:
                await channel.send("❌ I couldn't understand your bet. Please try again with a clearer description.")
                return
            
            # Check for invalid players
            if "invalid_players" in bet_data and bet_data["invalid_players"]:
                invalid_names = bet_data["invalid_players"]
                error_msg = f"❌ **Invalid player name{'s' if len(invalid_names) > 1 else ''}**: {', '.join(invalid_names)}"
                await channel.send(error_msg)
                
                # Show suggestions for similar player names if possible
                all_players = df["player_name"].unique()
                suggestions = []
                
                for invalid_name in invalid_names:
                    matches = get_close_matches(invalid_name, all_players, n=3, cutoff=0.6)
                    if matches:
                        suggestions.extend(matches)
                
                if suggestions:
                    await channel.send(f"Did you mean: {', '.join(suggestions[:3])}?")
                
                # Ask for the bet again with clearer instructions
                prompt_mode = state.get("bet_prompt_mode")
                await channel.send("What would you like to bet on? Just tell me the player and stat.\n*For example: 'LeBron over 25.5 points' or 'Curry assists'*")
                return
            
            # If we got here but have no valid players, prompt again
            if not bet_data.get("players"):
                await channel.send("❌ I couldn't identify any valid players in your bet. Please try again.")
                
                # Ask for the bet again with clearer instructions
                await channel.send("What would you like to bet on? Just tell me the player and stat.\n*For example: 'LeBron over 25.5 points' or 'Curry assists'*")
                return
    # Check if we're waiting for a new bet
    elif state.get("waiting_for_nlp_input", False):
        # Set up for NLP input
        user_nlp_bet_state[user_id] = state
        
        # Prompt for the new bet
        await channel.send("What would you like to bet on? Just tell me the player and stat.\n*For example: 'LeBron over 25.5 points' or 'Curry assists'*")
        return
    # If this is a follow-up response to a specific question
    elif not bet_input and state.get("waiting_for_input", False):
        # We're continuing with existing state and using the last_input that was already set
        bet_input = state.get("last_input", "")
        bet_data = state.get("bet_data")
        
        print(f"Follow-up response. Input: {bet_input}, Has bet data: {bet_data is not None}")
        
        # Make sure we have bet data
        if not bet_data or "players" not in bet_data or not bet_data["players"]:
            await channel.send("❌ Error: Lost bet information. Please start over.")
            # Reset the state
            user_nlp_bet_state[user_id] = {
                "stage": "initial", 
                "current_player_index": 0,
                "processing_complete": False,
                "bet_data": None
            }
            return
    else:
        # This is a new bet input, extract information
        if bet_input:
            bet_data = extract_bet_info(bet_input)
            print(f"New bet input. Extracted data: {bet_data}")
            
            if not bet_data:
                await channel.send("❌ I couldn't understand your bet. Please try again with a clearer description.")
                return
            
            # Check for invalid players immediately
            if "invalid_players" in bet_data and bet_data["invalid_players"]:
                invalid_names = bet_data["invalid_players"]
                error_msg = f"❌ **Invalid player name{'s' if len(invalid_names) > 1 else ''}**: {', '.join(invalid_names)}"
                await channel.send(error_msg)
                
                # Show suggestions for similar player names if possible
                all_players = df["player_name"].unique()
                suggestions = []
                
                for invalid_name in invalid_names:
                    matches = get_close_matches(invalid_name, all_players, n=3, cutoff=0.6)
                    if matches:
                        suggestions.extend(matches)
                
                if suggestions:
                    await channel.send(f"Did you mean: {', '.join(suggestions[:3])}?")
                
                # Show betting options again
                view = BettingWithCartView(user_id)
                await channel.send("Click a button below to continue:", view=view)
                return
            
            # Check if we have any valid players to process
            if not bet_data["players"]:
                await channel.send("❌ I couldn't identify any valid players in your bet. Please try again.")
                # Show betting options again
                view = BettingWithCartView(user_id)
                await channel.send("Click a button below to continue:", view=view)
                return
            
            # Reset state for new bet
            state = {
                "stage": "processing", 
                "bet_data": bet_data, 
                "current_player_index": 0, 
                "processing_complete": False,
                "last_input": bet_input,
                "waiting_for_input": False,
                "current_field": None
            }
            user_nlp_bet_state[user_id] = state
        else:
            # No input provided and not waiting for input
            bet_data = state.get("bet_data")
            if not bet_data or "players" not in bet_data or not bet_data["players"]:
                await channel.send("❌ No bet information found. Please start over.")
                return
    
    # At this point, we should have valid bet data
    print(f"Processing bet data: {bet_data}")
    
    # Process each player in the bet sequentially
    while state["current_player_index"] < len(bet_data["players"]):
        player_index = state["current_player_index"]
        player_data = bet_data["players"][player_index]
        
        print(f"Processing player at index {player_index}: {player_data}")
        
        # Validate and complete player information
        missing_info = await validate_and_complete_player_bet(player_data, user_id, channel)
        
        if missing_info:
            print(f"Missing info for player. Current field: {state.get('current_field')}")
            # Mark that we're waiting for user input
            state["waiting_for_input"] = True
            # Save the updated bet data back to state
            state["bet_data"] = bet_data
            # Make sure the state is saved
            user_nlp_bet_state[user_id] = state
            return
        
        # Update the player data in the bet_data
        bet_data["players"][player_index] = player_data
        # Save the updated bet data
        state["bet_data"] = bet_data
        # Move to the next player
        state["current_player_index"] += 1
        # Save the state
        user_nlp_bet_state[user_id] = state
    
    # If we've processed all players, check for entry fee
    if state["current_player_index"] >= len(bet_data["players"]):
        print(f"All players processed. Checking entry fee. Current entry fee: {bet_data.get('entry_fee')}")
        
        if bet_data.get("entry_fee") is None:
            # Ask for entry fee
            if state.get("asking_for_entry_fee", False):
                # Already asked, try to parse from the last message
                try:
                    entry_fee = float(state["last_input"].strip().replace('$', ''))
                    if entry_fee <= 0:
                        await channel.send("❌ Please enter a positive amount.")
                        state["waiting_for_input"] = True
                        user_nlp_bet_state[user_id] = state
                        return
                    
                    print(f"Setting entry fee to: {entry_fee}")
                    # Update the entry fee
                    bet_data["entry_fee"] = entry_fee
                    state["bet_data"] = bet_data
                    state["asking_for_entry_fee"] = False
                    state["waiting_for_input"] = False
                    user_nlp_bet_state[user_id] = state
                except ValueError:
                    await channel.send("❌ Invalid amount. Please enter a number like `10` or `25`.")
                    state["waiting_for_input"] = True
                    user_nlp_bet_state[user_id] = state
                    return
            else:
                # Skip asking for entry fee and go straight to finalizing the bet
                print("Skipping entry fee prompt and finalizing bet")
                await finalize_nlp_bet(bet_data, user_id, channel)
                state["processing_complete"] = True
                user_nlp_bet_state[user_id] = state
                return
        
        # All information is complete, finalize the bet
        print("Finalizing bet with complete information")
        await finalize_nlp_bet(bet_data, user_id, channel)
        state["processing_complete"] = True
        state["waiting_for_input"] = False
        user_nlp_bet_state[user_id] = state

async def validate_and_complete_player_bet(player_data, user_id, channel):
    state = user_nlp_bet_state[user_id]
    
    # Debug logging
    print(f"Validating player bet - User ID: {user_id}, Player Data: {player_data}, State: {state}")
    
    # Check if we're in the middle of resolving this player
    current_field = state.get("current_field")
    
    # Validate player name
    if player_data.get("name") is None or current_field == "name":
        if current_field == "name":
            # Try to resolve with user input
            player_names = df["player_name"].unique()
            matched = get_close_matches(state.get("last_input", ""), player_names, n=1, cutoff=0.6)
            resolved_name = matched[0] if matched else resolve_player_name(state.get("last_input", ""))
            
            if resolved_name and resolved_name in df["player_name"].values:
                player_data["name"] = resolved_name
                state["current_field"] = None  # Clear current field
            else:
                await channel.send("❌ Player not found. Please enter a valid NBA player name.")
                return True
        else:
            # Ask for player name with UI button
            view = FollowUpView(user_id)
            await channel.send("👤 Which player did you want to bet on? Click the button below to continue:", view=view)
            state["current_field"] = "name"
            return True
    
    # Validate stat type
    if player_data.get("stat_type") is None or current_field == "stat_type":
        if current_field == "stat_type":
            # Try to resolve with user input
            valid_stats = df[df["player_name"] == player_data["name"]]["stat_type"].unique()
            matched = get_close_matches(state.get("last_input", "").lower(), [s.lower() for s in valid_stats], n=1, cutoff=0.6)
            
            if matched:
                player_data["stat_type"] = matched[0]
                state["current_field"] = None  # Clear current field
            else:
                await channel.send(f"❌ Stat not found. Try one of these: {', '.join(valid_stats)}")
                return True
        else:
            # Ask for stat type with UI button
            view = FollowUpView(user_id)
            await channel.send(f"📊 What stat would you like to bet on for {player_data['name']}? (e.g., points, rebounds, assists)\nClick the button below to continue:", view=view)
            state["current_field"] = "stat_type"
            return True
    
    # Validate line value
    if player_data.get("line_value") is None or current_field == "line_value":
        if current_field == "line_value":
            # Try to resolve with user input
            try:
                val = float(state.get("last_input", ""))
                # Get available lines for this player and stat type
                player_filter = df["player_name"] == player_data["name"]
                stat_filter = df["stat_type"].str.lower() == player_data["stat_type"].lower()
                available_lines = df[player_filter & stat_filter]["line_value"].unique()
                
                # Check if the requested line exists
                if len(available_lines) == 0:
                    await channel.send(f"❌ No betting lines available for {player_data['name']} {player_data['stat_type']}.")
                    return True
                elif val in available_lines:
                    player_data["line_value"] = val
                    state["current_field"] = None  # Clear current field
                else:
                    # Line doesn't exist, show available options
                    closest_lines = sorted(available_lines, key=lambda x: abs(x - val))
                    suggestion = closest_lines[0] if closest_lines else None
                    
                    message = f"❌ The line {val} for {player_data['name']} {player_data['stat_type']} is not available.\n"
                    message += f"Available lines: {', '.join(map(str, available_lines))}"
                    
                    if suggestion:
                        message += f"\nDid you mean {suggestion}? Type this value or choose another from the list."
                    
                    await channel.send(message)
                    
                    # Add buttons for common actions
                    view = LineSelectionView(user_id, suggestion, available_lines)
                    await channel.send("Select an option:", view=view)
                    return True
            except ValueError:
                await channel.send("❌ Invalid input. Please type a number like `23.5`.")
                return True
        else:
            # Show available lines with UI button
            player_filter = df["player_name"] == player_data["name"]
            stat_filter = df["stat_type"].str.lower() == player_data["stat_type"].lower()
            available_lines = df[player_filter & stat_filter]["line_value"].unique()
            
            if len(available_lines) == 0:
                await channel.send(f"❌ No betting lines available for {player_data['name']} {player_data['stat_type']}.")
                return True
            
            view = FollowUpView(user_id)
            await channel.send(f"🔢 What line value would you like to bet on?\nAvailable lines: {', '.join(map(str, available_lines))}\nClick the button below to continue:", view=view)
            state["current_field"] = "line_value"
            return True
    
    # Validate bet type (over/under)
    if player_data.get("bet_type") is None or current_field == "bet_type":
        if current_field == "bet_type":
            # Try to resolve with user input
            bet_type = state.get("last_input", "").lower().strip()
            print(f"Processing bet type input: '{bet_type}'")
            
            if bet_type in ["over", "under"]:
                player_data["bet_type"] = bet_type
                state["current_field"] = None  # Clear current field
                print(f"Bet type set to: {bet_type}")
            else:
                await channel.send(f"❌ Please type either `over` or `under`. You entered: '{bet_type}'")
                return True
        else:
            # Ask for bet type with UI button
            view = FollowUpView(user_id)
            await channel.send(f"⬆️⬇️ Would you like to bet `over` or `under` {player_data['line_value']} {player_data['stat_type']} for {player_data['name']}?\nClick the button below to continue:", view=view)
            state["current_field"] = "bet_type"
            # Save player data to ensure it's not lost
            state["bet_data"]["players"][state["current_player_index"]] = player_data
            user_nlp_bet_state[user_id] = state
            return True
    
    # All fields are valid
    return False

# View for actions after bet confirmation with improved options
class PostBetActionView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="Place New Bet", style=ButtonStyle.primary, custom_id="place_more_bets_button")
    async def place_more_bets_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This option is for someone else.", ephemeral=True)
            return
        
        # Set mode to nlp_bet
        user_modes[self.user_id] = "nlp_bet"
        user_nlp_bet_state[self.user_id] = {"stage": "initial"}
        
        await interaction.response.defer()
        
        # Show the bet form with cart options
        view = BettingWithCartView(self.user_id)
        await interaction.channel.send("🎰 **Ready to Place Another Bet**\nClick a button below:", view=view)
    
    @ui.button(label="View Cart", style=ButtonStyle.success, custom_id="view_cart_post_bet")
    async def view_cart_post_bet(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        user_cart = user_carts.get(self.user_id, [])
        
        await interaction.response.defer()
        
        if not user_cart:
            await interaction.channel.send("🛒 Your cart is empty. Place a bet to add items to your cart.")
            
            # Show betting options
            view = BettingWithCartView(self.user_id)
            await interaction.channel.send("Click a button below to continue:", view=view)
            return
        
        # Display the cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, "Pending", filename="cart_preview.png")
        await interaction.channel.send(f"🛒 **Your Cart** - {len(user_cart)} bets", file=discord.File(cart_image))
        
        # Show cart management options
        view = CartManagementView(self.user_id)
        await interaction.channel.send("Cart Options:", view=view)
    
    @ui.button(label="View Betting Lines", style=ButtonStyle.secondary, custom_id="view_lines_button")
    async def view_lines_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This option is for someone else.", ephemeral=True)
            return
        
        # Set mode to search
        user_modes[self.user_id] = "search"
        
        await interaction.response.defer()
        
        # Show search instructions with exit button
        await interaction.channel.send(
            "🔎 **Betting Lines Search**\nEnter a team name, player, or stat type to view matching lines."
        )
        await interaction.channel.send("Or click the button below to exit:", view=ExitSearchView())
    
    @ui.button(label="Return to Main Menu", style=ButtonStyle.secondary, custom_id="post_bet_menu_button")
    async def post_bet_menu_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This option is for someone else.", ephemeral=True)
            return
        
        # Exit betting mode
        user_modes[self.user_id] = None
        
        await interaction.response.defer()
        await interaction.channel.send("🔙 Returning to Main Menu:", view=MainMenuView())

# Confirmation view for finalizing bets
class BetAmountView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="$10", style=ButtonStyle.primary, custom_id="bet_10")
    async def bet_10(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await process_bet_amount(10, self.user_id, interaction.channel)
    
    @ui.button(label="$20", style=ButtonStyle.primary, custom_id="bet_20")
    async def bet_20(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await process_bet_amount(20, self.user_id, interaction.channel)
    
    @ui.button(label="$50", style=ButtonStyle.primary, custom_id="bet_50")
    async def bet_50(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await process_bet_amount(50, self.user_id, interaction.channel)
    
    @ui.button(label="$100", style=ButtonStyle.primary, custom_id="bet_100")
    async def bet_100(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await process_bet_amount(100, self.user_id, interaction.channel)
    
    @ui.button(label="Custom Amount", style=ButtonStyle.secondary, custom_id="bet_custom")
    async def bet_custom(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        # Show a modal for custom amount
        modal = EntryFeeModal(self.user_id)
        await interaction.response.send_modal(modal)

class EntryFeeModal(ui.Modal, title="Enter Bet Amount"):
    entry_fee = ui.TextInput(label="Amount (in $)", placeholder="Enter amount (e.g., 25)", required=True)
    
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.entry_fee.value)
            if amount <= 0:
                await interaction.response.send_message("❌ Please enter a positive amount.", ephemeral=True)
                return
            
            await interaction.response.defer()
            await process_bet_amount(amount, self.user_id, interaction.channel)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

class FinalConfirmationView(ui.View):
    def __init__(self, user_id, bet_amount):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.bet_amount = bet_amount
    
    @ui.button(label="Confirm Bet", style=ButtonStyle.success, custom_id="final_confirm_button")
    async def final_confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await finalize_bet_with_amount(self.bet_amount, self.user_id, interaction.channel)
    
    @ui.button(label="Cancel", style=ButtonStyle.danger, custom_id="final_cancel_button")
    async def final_cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.channel.send("❌ Bet canceled. Your cart has been cleared.")
        
        # Clear the cart and state
        user_carts[self.user_id] = []
        if self.user_id in user_nlp_bet_state:
            del user_nlp_bet_state[self.user_id]
        
        # Return to main menu
        view = MainMenuView()
        await interaction.channel.send("Main Menu:", view=view)

class BetConfirmationView(ui.View):
    def __init__(self, user_id, bet_data):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.bet_data = bet_data
    
    @ui.button(label="Lock It In", style=ButtonStyle.success, custom_id="confirm_bet_button")
    async def confirm_bet_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Ask for bet amount
        view = BetAmountView(self.user_id)
        await interaction.channel.send("💰 **Enter Bet Amount** - How much would you like to bet in total?", view=view)
    
    @ui.button(label="View Cart", style=ButtonStyle.primary, custom_id="view_cart_from_confirmation")
    async def view_cart_from_confirmation(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        user_cart = user_carts.get(self.user_id, [])
        
        await interaction.response.defer()
        
        if not user_cart:
            await interaction.channel.send("🛒 Your cart is empty.")
            return
        
        # Display the full cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        entry_fee = user_cart[0]["entry_fee"] if user_cart else "Pending"
        cart_image = generate_bet_confirmation_image(display_data, entry_fee, filename="cart_preview.png")
        await interaction.channel.send(f"🛒 **Your Current Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''}:", file=discord.File(cart_image))
        
        # Show cart management options
        view = CartManagementView(self.user_id)
        await interaction.channel.send("Cart Options:", view=view)
        
        # Show confirmation options again
        view = BetConfirmationView(self.user_id, self.bet_data)
        await interaction.channel.send("Would you like to confirm this bet, add another bet, or cancel?", view=view)
    
    @ui.button(label="Add Another Bet", style=ButtonStyle.primary, custom_id="add_bet_button")
    async def add_bet_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        # Get user information
        user_id = self.user_id
        channel = interaction.channel
        current_entry_fee = self.bet_data.get("entry_fee", 0)
        user_cart = user_carts.get(user_id, [])
        
        # Reset the state to start a new bet but keep the cart
        user_nlp_bet_state[user_id] = {
            "stage": "initial", 
            "current_player_index": 0,
            "processing_complete": False,
            "bet_data": None,
            "cart": user_cart,
            "last_entry_fee": current_entry_fee  # Save the last entry fee
        }
        
        # We need to defer first
        await interaction.response.defer()
        
        # Display the current cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, current_entry_fee, filename="full_cart_preview.png")
        await channel.send(f"🛒 **Your Current Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''}", file=discord.File(cart_image))
        
        # Show betting options instead of asking to type in chat
        view = BettingWithCartView(user_id)
        await channel.send("Choose an option below to continue:", view=view)
    
    @ui.button(label="Cancel", style=ButtonStyle.danger, custom_id="cancel_bet_button")
    async def cancel_bet_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Clear the state
        if self.user_id in user_nlp_bet_state:
            del user_nlp_bet_state[self.user_id]
        
        # Show main menu
        await interaction.channel.send("❌ Bet canceled.")
        await interaction.channel.send("Main Menu:", view=MainMenuView())

# View for selecting a line when the original line is invalid
class LineSelectionView(ui.View):
    def __init__(self, user_id, suggestion=None, available_lines=None):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.suggestion = suggestion
        self.available_lines = available_lines or []
        
        # If we have a suggestion, add a button for it
        if suggestion is not None:
            self.add_item(ui.Button(label=f"Use {suggestion}", style=ButtonStyle.primary, custom_id=f"use_line_{suggestion}"))
    
    @ui.button(label="Try Different Bet", style=ButtonStyle.secondary, custom_id="try_different_bet")
    async def try_different_bet(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Reset the state
        user_nlp_bet_state[self.user_id] = {
            "stage": "initial", 
            "current_player_index": 0,
            "processing_complete": False,
            "bet_data": None
        }
        
        # Show the bet form again
        view = NaturalBetView()
        await interaction.channel.send("Click the button below to place a new bet:", view=view)

# View for trying again when a bet has invalid lines
class TryAgainBetView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="Place Another Bet", style=ButtonStyle.primary, custom_id="place_another_bet")
    async def place_another_bet(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Show the bet form again
        view = NaturalBetView()
        await interaction.channel.send("Click the button below to place a new bet:", view=view)
    
    @ui.button(label="Return to Main Menu", style=ButtonStyle.secondary, custom_id="return_to_menu")
    async def return_to_menu(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Return to main menu
        await interaction.channel.send("Main Menu:", view=MainMenuView())

# View for adding another bet with options for entry fee
class AddBetOptionsView(ui.View):
    def __init__(self, user_id, current_fee=None):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @ui.button(label="Add Another Bet", style=ButtonStyle.primary, custom_id="add_another_bet_button")
    async def add_another_bet_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        # Update state for the next bet
        state = user_nlp_bet_state.get(self.user_id, {})
        state["bet_prompt_mode"] = "adding_bet"
        user_nlp_bet_state[self.user_id] = state
        
        await interaction.response.defer()
        
        # Show the current cart first
        user_cart = user_carts.get(self.user_id, [])
        
        if user_cart:
            # Display the cart contents
            display_data = [
                {
                    "name": bet["player_name"],
                    "stat_type": bet["stat_type"],
                    "line_value": bet["line_value"],
                    "bet_type": bet["bet_type"]
                }
                for bet in user_cart
            ]
            
            # Generate and display the cart image
            cart_image = generate_bet_confirmation_image(display_data, None, filename="current_cart.png")
            await interaction.channel.send(f"🛒 **Your Current Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''}", file=discord.File(cart_image))
        
        # Prompt for the new bet with clear instructions
        await interaction.channel.send("What would you like to bet on? Just tell me the player and stat.\n*For example: 'LeBron over 25.5 points' or 'Curry assists'*")
        
        # Set up state for NLP processing
        state = user_nlp_bet_state.get(self.user_id, {})
        state["waiting_for_nlp_input"] = True
        state["nlp_context"] = "adding_bet"
        user_nlp_bet_state[self.user_id] = state
    
    @ui.button(label="View Cart", style=ButtonStyle.secondary, custom_id="view_cart_button")
    async def view_cart_button(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This bet belongs to someone else.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Show the current cart
        user_cart = user_carts.get(self.user_id, [])
        
        if not user_cart:
            await interaction.channel.send("❌ Your cart is empty.")
            return
        
        # Display the cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, None, filename="current_cart.png")
        await interaction.channel.send(f"🛒 **Your Current Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''}", file=discord.File(cart_image))
        
        # Show cart management options
        view = CartManagementView(self.user_id)
        await interaction.channel.send("Cart Options:", view=view)
        
        # Set up state to indicate we're editing all amounts
        state = user_nlp_bet_state.get(self.user_id, {})
        state["editing_all_amounts"] = True
        user_nlp_bet_state[self.user_id] = state
    @ui.button(label="View Cart", style=ButtonStyle.success, custom_id="view_cart_from_options")
    async def view_cart_from_options(self, interaction: discord.Interaction, button: ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart belongs to someone else.", ephemeral=True)
            return
        
        user_cart = user_carts.get(self.user_id, [])
        
        await interaction.response.defer()
        
        if not user_cart:
            await interaction.channel.send("🛒 Your cart is empty. Place a bet to add items to your cart.")
            return
        
        # Display the cart contents
        display_data = [
            {
                "name": bet["player_name"],
                "stat_type": bet["stat_type"],
                "line_value": bet["line_value"],
                "bet_type": bet["bet_type"]
            }
            for bet in user_cart
        ]
        
        # Generate and display the cart image
        cart_image = generate_bet_confirmation_image(display_data, "Pending", filename="cart_preview.png")
        await interaction.channel.send(f"🛒 **Your Cart** - {len(user_cart)} bets", file=discord.File(cart_image))
        
        # Show cart management options
        view = CartManagementView(self.user_id)
        await interaction.channel.send("Cart Options:", view=view)

# Process the confirmation of a bet
async def process_bet_amount(amount, user_id, channel):
    # Get the user's cart
    user_cart = user_carts.get(user_id, [])
    
    if not user_cart:
        await channel.send("❌ Your cart is empty. Please add bets first.")
        return
    
    # Update all bets in the cart with the entry fee
    for bet in user_cart:
        bet["entry_fee"] = amount
    
    # Display the cart with the entry fee
    display_data = [
        {
            "name": bet["player_name"],
            "stat_type": bet["stat_type"],
            "line_value": bet["line_value"],
            "bet_type": bet["bet_type"]
        }
        for bet in user_cart
    ]
    
    # Generate and display the cart image with entry fee
    cart_image = generate_bet_confirmation_image(display_data, amount, filename="cart_with_amount.png")
    await channel.send(f"🛒 **Your Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''} with ${amount} bet", file=discord.File(cart_image))
    
    # Show final confirmation view
    view = FinalConfirmationView(user_id, amount)
    await channel.send("Please confirm your final bet:", view=view)

async def finalize_bet_with_amount(amount, user_id, channel):
    # Get the user's cart
    user_cart = user_carts.get(user_id, [])
    
    if not user_cart:
        await channel.send("❌ Your cart is empty. Please add bets first.")
        return
    
    # Generate the final payload with the entry fee
    payload = generate_bets_payload(user_id, amount, user_cart)
    
    # Display the cart with the entry fee
    display_data = [
        {
            "name": bet["player_name"],
            "stat_type": bet["stat_type"],
            "line_value": bet["line_value"],
            "bet_type": bet["bet_type"]
        }
        for bet in user_cart
    ]
    
    # Generate and display the cart image with entry fee
    cart_image = generate_bet_confirmation_image(display_data, amount, filename="final_cart.png")
    await channel.send(f"🎉 **Success!** Your bet of ${amount} has been confirmed!", file=discord.File(cart_image))
    
    # Show the API payload
    await channel.send(f"📦 Final payload sent to Strike API:\n```json\n{json.dumps(payload, indent=2)}\n```")
    
    # Clear the cart and state for the next bet
    user_carts[user_id] = []
    if user_id in user_nlp_bet_state:
        del user_nlp_bet_state[user_id]
    
    # Show buttons for next actions
    view = PostBetActionView(user_id)
    await channel.send("👏 **Bet Placed Successfully!** What would you like to do next?", view=view)

async def process_bet_confirmation(bet_data, user_id, channel):
    # Save a copy of the current bet data for display (without entry fee)
    current_bet_data = {
        "players": []
    }
    
    for player in bet_data["players"]:
        current_bet_data["players"].append({
            "name": player["name"],
            "bet_type": player["bet_type"],
            "line_value": player["line_value"],
            "stat_type": player["stat_type"]
        })
    
    # Get the user's cart - the bet is already in the cart, so we don't need to add it again
    user_cart = user_carts.get(user_id, [])
    
    # First display the full cart contents
    full_display_data = [
        {
            "name": bet["player_name"],
            "stat_type": bet["stat_type"],
            "line_value": bet["line_value"],
            "bet_type": bet["bet_type"]
        }
        for bet in user_cart
    ]
    
    # Generate and display the full cart image (without entry fee)
    full_cart_image = generate_bet_confirmation_image(full_display_data, None, filename="full_cart_preview.png")
    await channel.send(f"🛒 **Your Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''}", file=discord.File(full_cart_image))
    
    # Then ask for bet amount
    view = BetAmountView(user_id)
    await channel.send("💰 **Enter Bet Amount** - How much would you like to bet in total?", view=view)
    
    # Show the API payload
    await channel.send(f"📦 Final payload sent to Strike API:\n```json\n{json.dumps(payload, indent=2)}\n```")
    
    # Clear the cart and state for the next bet
    user_carts[user_id] = []
    if user_id in user_nlp_bet_state:
        del user_nlp_bet_state[user_id]
    
    # Show buttons for next actions with clear labels including cart options
    view = PostBetActionView(user_id)
    await channel.send("👏 **Bet Placed Successfully!** What would you like to do next?", view=view)

async def finalize_nlp_bet(bet_data, user_id, channel):
    # Final validation of all bet lines against the database
    invalid_bets = []
    for i, player in enumerate(bet_data["players"]):
        player_filter = df["player_name"] == player["name"]
        stat_filter = df["stat_type"].str.lower() == player["stat_type"].lower()
        line_filter = df["line_value"] == player["line_value"]
        
        # Check if this exact bet exists in the database
        if df[player_filter & stat_filter & line_filter].empty:
            invalid_bets.append(i)
    
    # If there are invalid bets, notify the user and don't proceed
    if invalid_bets:
        error_msg = "❌ The following bets have invalid lines that don't exist in our database:\n"
        for i in invalid_bets:
            player = bet_data["players"][i]
            error_msg += f"- {player['name']} {player['bet_type']} {player['line_value']} {player['stat_type']}\n"
        
        await channel.send(error_msg)
        
        # Show a button to place another bet
        view = TryAgainBetView(user_id)
        await channel.send("Please try again with valid betting lines.", view=view)
        
        # Reset the state to start over
        user_nlp_bet_state[user_id] = {
            "stage": "initial", 
            "current_player_index": 0,
            "processing_complete": False,
            "bet_data": None
        }
        return
    
    # Automatically add the bet to the cart as soon as it's validated
    user_cart = user_carts.setdefault(user_id, [])
    
    # Add the validated bet to the cart (without entry fee)
    for player in bet_data["players"]:
        bet = {
            "entry_fee": None,  # Set entry fee to None
            "player_name": player["name"],
            "bet_type": player["bet_type"],
            "line_value": player["line_value"],
            "stat_type": player["stat_type"]
        }
        user_cart.append(bet)
    
    # Update the state to include the cart (without entry fee references)
    user_nlp_bet_state[user_id] = {
        "stage": "confirmation",
        "bet_data": bet_data,
        "cart": user_cart
    }
    
    # Display only the full cart contents
    full_display_data = [
        {
            "name": bet["player_name"],
            "stat_type": bet["stat_type"],
            "line_value": bet["line_value"],
            "bet_type": bet["bet_type"]
        }
        for bet in user_cart
    ]
    
    # Generate and display only the full cart image (without entry fee)
    full_cart_image = generate_bet_confirmation_image(full_display_data, None, filename="full_cart_preview.png")
    await channel.send(f"🛒 **Your Cart** - {len(user_cart)} bet{'s' if len(user_cart) > 1 else ''}", file=discord.File(full_cart_image))
    
    # Show confirmation buttons
    view = BetConfirmationView(user_id, bet_data)
    await channel.send("Would you like to confirm this bet, add another bet, or cancel?", view=view)

# Run bot
client.run(DISCORD_TOKEN)
