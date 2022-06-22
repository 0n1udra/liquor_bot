import image_rescale, requests, discord, random, sys, os
from discord_components import DiscordComponents, Button, ButtonStyle,  Select, SelectOption, ComponentsBot
from bs4 import BeautifulSoup
from datetime import datetime

__version__ = "1a"
__date__ = '2022/04/12'
__author__ = "DT"
__email__ = "dt01@pm.me"
__license__ = "GPL 3"
__status__ = "Development"

token_file = f'{os.getenv("HOME")}/keys/liquor_bot.token'
bot_path = os.path.dirname(os.path.abspath(__file__))
box_photos_path = '~/Pictures/liquor_boxes/'
bot_channel_id = 988549339808952371
data_dict = {'Name': 'N/A', 'Details': 'N/A', 'Code': 'N/A', 'Pack': 'N/A', 'Inventory': 'N/A', 'Ordered': 'N/A', 'Have': 'N/A', 'Icon': '\U00002754'}
# Codes stored for diff feature.
active_codes = {'testUser': ['12']}

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
    await bot_channel.send(f':white_check_mark: **Bot PRIMED** {datetime.now().strftime("%X")}')

@bot.event
async def on_button_click(interaction):
    # Need to respond with type=6, or proceeding code will execute twice.
    await interaction.respond(type=6)
    ctx = await bot.get_context(interaction.message)
    await ctx.invoke(bot.get_command(str(interaction.custom_id)))


# ========== Web Scraper
def get_soup(site_url):
    # Requests sandown.us/minutes-and-agenda with random user agent.
    user_agents = ["Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
                   "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
                   "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"]
    headers = {'User-Agent': random.choice(user_agents)}

    try: site_request = requests.get(site_url, headers=headers)
    except: return False
    else: return BeautifulSoup(site_request.text, 'html.parser')


def text_parser(text, index, split_str=None, slice=2):
    # E.g. 'Class: 898  IMPORTED VERMOUTH                        Status: A 070104' > 'Imported    return_data.update({'Name': product_code,'Code': product_code, 'Icon': '\U0001F6AB'}) vermouth'
    return ' '.join(text[index].split(split_str)[0].split()[slice:])

def liquor_parser(product_code):
    """Parses data into dictionary."""

    # E.g. [{'Name': 'M & R Sweet Vermouth', 'Details': 'BACARDI USA INC, IMPORTED VERMOUTH, ITALIAN VERMOUTH ',
    #       'Pack': 6, 'Inventory': 8, 'Ordered': 12}
    return_data = data_dict.copy()
    return_data.update({'Name': product_code,'Code': product_code, 'Icon': '\U0001F6AB'})

    # Product details page, Name, bottles perpack, etc.
    product_details_url = f'https://ice.liquor.nh.gov/public/default.asp?Category=inquiries&Service=brandinfopost&req={product_code}'
    # Inventory info page, On hand bottles and ordered.
    product_inventory_url = f'https://ice.liquor.nh.gov/public/default.asp?Category=inquiries&Service=prodfindpost&req={product_code}'
    try:
        if soup := get_soup(product_details_url):
            if soup_text := soup.find_all('pre')[0].text:
                text = [i.strip() for i in soup_text.split('\n') if i.strip()]
                return_data['Name'] = text_parser(text, 0, 'Proof%:', slice=0)
                return_data['Details'] = f"{text[1].strip()}, {text_parser(text, 2, 'Status:')}, {text_parser(text, 3, 'Listed:')}, {text_parser(text, 5, 'Last EPSS:')}"
                return_data['Pack'] = text[9].split('Physical Pack: ')[-1]
    except: pass

    try:
        if soup := get_soup(product_inventory_url):
            if table := soup.find_all('table')[1]:
                for tr in table.find_all('tr'):
                    for a in tr.find_all('a'):
                        if '41 - Seabrook' in a.text:
                            td_data = tr.find_all('td')
                            return_data['Inventory'] = td_data[1].text.strip()
                            return_data['Ordered'] = td_data[2].text.strip()

        if int(return_data['Inventory']) / int(return_data['Pack']) >= 1: return_data['Icon'] = '\U00002705'
        else: return_data['Icon'] = '\U0000274C'
    except: pass

    return return_data

def get_product_data(product_code=None):
    """Fetches and parses product data."""

    liquor_data = []

    # Makes sure each code is usable first by converting to int and back.
    try: product_codes = [str(int(i)) for i in product_code]
    except: return False

    if not product_code: return False
    for i in product_codes:
        liquor_data.append(liquor_parser(i))

    return liquor_data


# ========== Commands
@bot.command(aliases=['i', 'I', 'inv', 'Inv', 'Check', 'check'])
async def inventorycheck(ctx, *product_code):
    """Gets product data by store code(s)."""

    # Lets user use codes from active_codes.
    start_range, end_range = 0, None
    if 'codes' in product_code or 'c' in product_code:
        # Optionally specify code group, use codeget() to see groups.
        if len(product_code) == 2:
            try:
                start_range = int(product_code[-1]) * 5 - 5
                end_range = start_range + 5
            except:
                await ctx.send("Could not get number group")
                return
        product_code = active_codes[ctx.message.author.name][start_range:end_range]

    await ctx.send(f"***Checking Inventory...***")
    product_data = get_product_data(product_code)

    if not product_data:
        await ctx.send("No inventory data available.")
        return False

    # TODO Add feature showing what code has error (like a letter instead of number)

    embed = discord.Embed(title='Inventory')
    for i in product_data:
        embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"*Pack:* **__{i['Pack']}__** | *On-hand:* **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`", inline=False)
    await ctx.send(embed=embed)
    lprint(f"Fetched Product: {product_code}")

@bot.command(aliases=['d', 'D', 'dif', 'Diff'])
async def codediff(ctx, *product_code):
    """Checks if codes are in active_codes."""

    for i in product_code:
        if i in active_codes[ctx.message.author.name]:
            await ctx.send(f"Match: {i}")

@bot.command(aliases=[ 'a',  'A', 'Add', 'add', 'addcode'])
async def codeadd(ctx, *product_code):
    """Add codes to active_codes."""
    global active_codes

    # So each user can have their own set of codes.
    if ctx.message.author.name not in active_codes:
        active_codes[ctx.message.author.name] = []

    try:
        new_codes = []
        for i in product_code:
            # Makes sure no duplicate codes.
            if i not in active_codes[ctx.message.author.name]:
                new_codes.append(str(int(i)))
        active_codes[ctx.message.author.name].extend(new_codes)
    except:
        await ctx.send("Not all were numbers.")
        return

    await ctx.send("**Added codes**")
    await ctx.invoke(bot.get_command("codeget"))
    lprint(f"Code added: {product_code}")

@bot.command(aliases=[ 'r', 'R', 'remove', 'Remove'])
async def coderemove(ctx, *product_code):
    """Removes active codes."""

    global active_codes

    removed_codes, new_codes = [], []
    for i in active_codes[ctx.message.author.name]:
        # Skips adding code to active_codes if matched.
        if i in product_code:
            removed_codes.append(i)
            continue
        new_codes.append(i)
    active_codes[ctx.message.author.name] = new_codes.copy()

    await ctx.send(f"Removed codes: {', '.join(removed_codes)}")
    lprint(f'Removed codes: {product_code}')

@bot.command(aliases=['cc', 'Cc', 'CC', 'Clear', 'clear'])
async def codeclear(ctx, *args):
    """Clears active_codes."""

    global active_codes

    if args: return

    active_codes[ctx.message.author.name].clear()
    await ctx.send("Cleared active codes")
    lprint('Cleared codes')

@bot.command(aliases=['c', 'C', 'Code', 'Codes', 'codes'])
async def codeget(ctx, group=''):
    """Fetches current active codes."""

    if not active_codes[ctx.message.author.name]:
        await ctx.send("No active codes.")
        return

    # Get specified number group
    start_range, end_range = 0, None
    try:
        start_range = int(group) * 5 - 5
        end_range = start_range + 5
    except: pass

    text = ''
    counter = 0
    for i in active_codes[ctx.message.author.name][start_range:end_range]:
        if group and counter % 5 == 0: text += f"**Group {group}** -----\n"
        # Display codes in groups of 5
        elif counter == 0: text += '**Group 1** ----------\n'
        elif counter % 5 == 0 and counter > 1:
            text += f'**{(counter / 5) + 1:.0f}** ----------\n'
        counter += 1

        text += f'{i}\n'

    await ctx.send(f"**Active Codes:**\n{text}")
    await ctx.send("----------END----------")
    lprint('Fetched codes')

# ===== Photo
@bot.command(aliases=['b', 'B', 'box', 'Box', 'Boxphoto', 'boxpicture', 'Boxpicture', 'P', 'p', 'picture', 'Picture'])
async def boxphoto(ctx, *product_code):
    """Gets photo of liquor box from code."""

    # Lets user use codes from active_codes.
    start_range, end_range = 0, None
    if 'codes' in product_code or 'c' in product_code:
        # Optionally specify code group, use codeget() to see groups.
        if len(product_code) == 2:
            try:
                start_range = int(product_code[-1]) * 5 - 5
                end_range = start_range + 5
            except:
                await ctx.send("Could not get number group")
                return
        product_code = active_codes[ctx.message.author.name][start_range:end_range]

    await ctx.send(f"***Checking Inventory and Fetching Images...***")
    product_data = get_product_data(product_code[start_range:end_range])

    if not product_data:
        await ctx.send("No inventory data available.")
        return False

    for i in product_data:
        embed = discord.Embed(title='Inventory')
        try: file = discord.File(f"{box_photos_path}/{i['Code']}.jpg", filename=f"{i['Code']}.jpg")
        except:
            embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"*Pack:* **__{i['Pack']}__** | *On-hand:* **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`\nNO AVAILABLE PHOTO", inline=False)
            await ctx.send(embed=embed)
        else:  # If found photo
            embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"*Pack:* **__{i['Pack']}__** | *On-hand:* **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`",inline=False)
            embed.set_image(url=f"attachment://{i['Code']}.jpg")
            await ctx.send(file=file, embed=embed)

    lprint(f'Fetched photo for: {product_code}')

@bot.command(aliases=['bi', 'Bi', 'Boximage', 'Image', 'image'])
async def boxupimageonly(ctx, product_code):
    try:
        file = discord.File(f"{box_photos_path}/{product_code}.jpg", filename=f"{product_code}.jpg")
    except:
        await ctx.send("Not Image Found")
        return
    else:  # If found photo
        await ctx.send(f'Image for: {product_code}', file=file)
        lprint(f"Fetched image: {product_code}")

@bot.command(aliases=['bu', 'Bu', 'Boxupload', 'u', 'U', 'upload', 'Upload'])
async def boxupload(ctx, product_code):
    try: product_code = str(int(product_code))
    except:
        await ctx.send("Please try again with corresponding product code")
        return

    for attachment in ctx.message.attachments:
        await attachment.save(f'{box_photos_path}/{product_code}.jpg')

    await ctx.send(f"Received new box photo for: {product_code}")
    image_rescale.rescale(f"{box_photos_path}/{product_code}.jpg", 50)
    await ctx.invoke(bot.get_command("boxphoto"), product_code)
    lprint(f"New box photo: {box_photos_path}/{product_code}.jpg")

@bot.command(aliases=['br', 'Br', 'Boxrename', 'rename', 're', 'Re', 'Rename'])
async def boximagerename(ctx, product_code, new_code):
    try:
        os.rename(f"{box_photos_path}/{product_code}.jpg", f"{box_photos_path}/{new_code}.jpg")
    except:
        await ctx.send("Error renaming image.")
        return
    await ctx.send(f"Image Renamed: {product_code}.jpg > {new_code}.jpg")
    lprint(f"Image Renamed: {product_code}.jpg > {new_code}.jpg")

@bot.command(aliases=['?'])
async def shortcuts(ctx):

    await ctx.send("""```
Command     - Description, example
c, codes    - Show current active codes
a, add      - Add active codes, a 7221 6660 982
r, remove   - Remove active codes, r 6660
d, diff     - Check if code in active codes, d 7221 982
i, inv      - Check inventory, i 7221 6660, i codes
b, box      - Checks inventory and adds boxes
u, upload   - Upload new box image, u 7221
re, rename  - Rename image, re 7221 7222
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
