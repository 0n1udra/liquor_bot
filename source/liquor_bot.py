import requests, discord, random, sys, os
from discord_components import DiscordComponents, Button, ButtonStyle,  Select, SelectOption, ComponentsBot
from bs4 import BeautifulSoup
from datetime import datetime

token_file = f'{os.getenv("HOME")}/keys/liquor_bot.token'
bot_path = os.path.dirname(os.path.abspath(__file__))
bot_channel_id = 988549339808952371
data_dict = {'Name': 'N/A', 'Details': 'N/A', 'Code': 'N/A', 'Pack': 'N/A', 'Inventory': 'N/A', 'Ordered': 'N/A', 'Have': 'N/A', 'Icon': '\U00002754'}
# Codes stored for diff feature.
active_codes = []

if os.path.isfile(token_file):
    with open(token_file, 'r') as file: TOKEN = file.readline()
else:
    print("Missing Token File:", token_file)
    sys.exit()

def lprint(msg): print(f'{datetime.today()} | {msg}')

bot = ComponentsBot(command_prefix='')

# ========== Discord
@bot.event
async def on_ready():
    lprint("Bot Connected")
    await bot.wait_until_ready()
    bot_channel = bot.get_channel(bot_channel_id)
    await bot_channel.send('**Bot PRIMED** :white_check_mark:')

@bot.event
async def on_button_click(interaction):
    # Need to respond with type=6, or proceeding code will execute twice.
    await interaction.respond(type=6)
    ctx = await bot.get_context(interaction.message)
    await ctx.invoke(bot.get_command(str(interaction.custom_id)))


# ========== Web Scraper
def liquor_scraper(site_url):
    # Requests sandown.us/minutes-and-agenda with random user agent.
    user_agents = ["Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
                   "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
                   "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"]
    headers = {'User-Agent': random.choice(user_agents)}

    try: site_request = requests.get(site_url, headers=headers)
    except: return False
    else: return BeautifulSoup(site_request.text, 'html.parser')

def get_product_data(product_code=None):
    """Fetches and parses product data."""

    if not product_code: return False

    # E.g. [{'Name': 'M & R Sweet Vermouth', 'Details': 'BACARDI USA INC, IMPORTED VERMOUTH, ITALIAN VERMOUTH ',
    #       'Pack': 6, 'Inventory': 8, 'Ordered': 12}
    return_data = data_dict.copy()
    return_data.update({'Name': product_code,'Code': product_code})

    # Product details page, Name, bottles perpack, etc.
    product_details_url = f'https://ice.liquor.nh.gov/public/default.asp?Category=inquiries&Service=brandinfopost&req={product_code}'
    # Inventory info page, On hand bottles and ordered.
    product_inventory_url = f'https://ice.liquor.nh.gov/public/default.asp?Category=inquiries&Service=prodfindpost&req={product_code}'

    def parser(text, index, split_str=None, slice=2):
        # E.g. 'Class: 898  IMPORTED VERMOUTH                        Status: A 070104' > 'Imported vermouth'
        return ' '.join(text[index].split(split_str)[0].split()[slice:])

    if soup := liquor_scraper(product_details_url):
        if soup_text := soup.find_all('pre')[0].text:
            text = [i.strip() for i in soup_text.split('\n') if i.strip()]
            return_data['Name'] = parser(text, 0, 'Proof%:', slice=0)
            return_data['Details'] = f"{text[1].strip()}, {parser(text, 2, 'Status:')}, {parser(text, 3, 'Listed:')}, {parser(text, 5, 'Last EPSS:')}"
            return_data['Pack'] = text[9].split('Physical Pack: ')[-1]

    if soup := liquor_scraper(product_inventory_url):
        if table := soup.find_all('table')[1]:
            for tr in table.find_all('tr'):
                for a in tr.find_all('a'):
                    if '41 - Seabrook' in a.text:
                        td_data = tr.find_all('td')
                        return_data['Inventory'] = td_data[1].text.strip()
                        return_data['Ordered'] = td_data[2].text.strip()

    # Checks if have on-hand bottles
    try:
        if int(return_data['Inventory']) / int(return_data['Pack']) >= 1: return_data['Icon'] = '\U00002705'
        else: return_data['Icon'] = '\U0000274C'
    except: pass

    return return_data


# ========== Commands
@bot.command(aliases=['check'])
async def getitem(ctx, *product_code):
    """Gets product data by store code(s)."""

    global active_codes

    product_data = []
    if 'codes' in product_code:
        product_code = active_codes.copy()

    await ctx.send(f"***Checking Inventory...***")

    # Tries to get product data if able to convert to int
    try: product_data.append(get_product_data(int(product_code)))
    except:
        try:  # If received multiple product codes.
            product_codes = [int(i) for i in product_code]
            # If product_codes list comprehension successful, gets product data with each code.
            for i in product_codes:
                data = data_dict.copy()
                try: product_data.append(get_product_data(i))
                except:
                    data.update({'Name': i, 'Code': i, 'Icon': '\U0001F6AB'})
                    product_data.append(data)
        except: product_data = None

    if not product_data:
        await ctx.send("Error checking codes.")
        return False

    # TODO Add feature showing what code has error (like a letter instead of number)

    embed = discord.Embed(title='Inventory')
    for i in product_data:
        embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"*Pack:* **__{i['Pack']}__** | *On-hand:* **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`", inline=False)
    await ctx.send(embed=embed)
    lprint(f"Fetched Product: {product_code}")

@bot.command(aliases=['d'])
async def diff(ctx, *product_code):
    """Checks if codes are in active_codes."""

    for i in product_code:
        if i in active_codes:
            await ctx.send(f"Match: {i}")

@bot.command(aliases=['addcode', 'add', 'a'])
async def codeadd(ctx, *product_code):
    """Add codes to active_codes."""
    global active_codes

    try:
        # Add code if not already added
        for i in product_code:
            if i not in active_codes:
                active_codes.append(str(int(i)))
    except:
        await ctx.send("Not all were numbers.")
        return
    await ctx.send("**Added codes**")
    await ctx.invoke(bot.get_command("codeget"))
    lprint(f"Code added: {product_code}")

@bot.command(aliases=['remove', 'r'])
async def coderemove(ctx, *product_code):
    """Removes active codes."""

    global active_codes
    new_codes = []
    for i in active_codes:
        if i in product_code: continue
        new_codes.append(i)
    active_codes = new_codes.copy()
    await ctx.send(f"Removed codes: {str(*product_code)}")
    lprint(f'Removed codes: {product_code}')

@bot.command(aliases=['cc', 'clear'])
async def codeclear(ctx):
    global active_codes
    active_codes.clear()
    await ctx.send("Cleared active codes")
    lprint('Cleared codes')

@bot.command(aliases=['c', 'codes'])
async def codeget(ctx):
    """Fetches current active codes."""

    global active_codes

    if not active_codes:
        await ctx.send("No active codes.")
        return

    text = ''
    counter = 0
    for i in active_codes:
        text += str(i) + '\n'
        counter += 1
        if counter == 5:
            text += '-----\n'
            counter = 0

    await ctx.send(f"**Active Codes:**\n{text}----------")
    lprint('Fetched codes')

@bot.command(aliases=['?'])
async def shortcuts(ctx):

    await ctx.send("""```
c, codes    - Show current active codes
a, add      - Add active codes, a 7221 6660 982
r, remove   - Remove active codes, r 6660
d, diff     - Check if code in active codes, d 7221 982
check       - Check inventory, check 7221 6660, check c
```""")


# ===== Msc
@bot.command(aliases=['rbot', 'rebootbot', 'botrestart', 'botreboot'])
async def restartbot(ctx, now=''):
    """Restart this bot."""

    lprint("Restarting bot...")
    os.chdir('/')
    os.chdir(bot_path)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.command(aliases=['updatebot', 'botupdate', 'git', 'update'])
async def gitupdate(ctx):
    """Gets update from GitHub."""

    await ctx.send("***Updating from GitHub...*** :arrows_counterclockwise:")
    os.chdir(bot_path)
    os.system('git pull')
    await ctx.invoke(bot.get_command("restartbot"))

bot.run(TOKEN)
