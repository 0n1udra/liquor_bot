import image_rescale, datetime, requests, discord, random, sys, os
from discord_components import DiscordComponents, Button, ButtonStyle,  Select, SelectOption, ComponentsBot
from bs4 import BeautifulSoup

__version__ = "1.2a"
__date__ = '2022/04/12'
__author__ = "DT"
__email__ = "dt01@pm.me"
__license__ = "GPL 3"
__status__ = "Development"

# ========== Variable & Funcs
bot_path = os.path.dirname(os.path.abspath(__file__))
bot_log_file = bot_path + '/liquor_log.txt'
box_photos_path = f'/home/{os.getlogin()}/Pictures/liquor_boxes'
token_file = f'{os.getenv("HOME")}/keys/liquor_bot.token'
bot_channel_id = 988549339808952371
ctx = "liquor_bot.py"  # For logging

data_points = ['Name', 'Details', 'Code', 'Pack', 'Inventory', 'Ordered', 'Have']
data_dict = {k:'N/A' for k in data_points}
data_dict.update({'Icon':'\U00002754'})
active_codes = {'testUser': ['12']}  # Each user gets own list of active codes

def lprint(ctx, msg):
    """Prints and Logs events in file."""

    try: user = ctx.message.author
    except: user = ctx

    output = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ({user}): {msg}"
    print(output)

    # Logs output.
    with open(bot_log_file, 'a') as file:
        file.write(output + '\n')

def check_active(context):
    """Checks if user has a list in active_codes."""

    try:
        _ = active_codes[context.message.author.name]
        return True
    except: return False

def remove_dupes(input_list): return sorted(set(input_list), key=lambda x: input_list.index(x))

def format(codes): return ', '.join(codes)

async def check_use_ac(ctx, paramters):
    """Get codes or a group from active_codes if received right parameter."""

    use_ac, start_range, end_range = False, 0, None
    for i in ['c', 'C', 'Code', 'code', 'Codes', 'codes']:
        if i in paramters: use_ac = True

    # If not using active_codes list, will remove dupes from input and return it.
    if not use_ac: return remove_dupes(paramters)

    if not check_active(ctx):
        await ctx.send("No active codes")
        return False

    # Optionally specify code group, use codeget() to see groups.
    if len(paramters) == 2:
        try:  # Slices list up to extract the 5 specified codes of group.
            start_range = int(paramters[-1]) * 5 - 5
            end_range = start_range + 5
        except:
            await ctx.send("Could not group")
            return
    return active_codes[ctx.message.author.name][start_range:end_range]

# ========== Discord Setup
if os.path.isfile(token_file):
    with open(token_file, 'r') as file: TOKEN = file.readline()
else:
    print("Missing Token File:", token_file)
    sys.exit()
bot = ComponentsBot(command_prefix='')

@bot.event
async def on_ready():
    lprint(ctx, "Bot Connected")
    await bot.wait_until_ready()
    bot_channel = bot.get_channel(bot_channel_id)
    await bot_channel.send(f':white_check_mark: **Bot PRIMED** {datetime.datetime.now().strftime("%X")}')

@bot.event
async def on_button_click(interaction):
    # Need to respond with type=6, or proceeding code will execute twice.
    await interaction.respond(type=6)
    ctx = await bot.get_context(interaction.message)
    await ctx.invoke(bot.get_command(str(interaction.custom_id)))


# ========== Web Scraper
def get_soup(site_url):
    """Gets soup from request.text."""

    user_agents = ["Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
                   "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
                   "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"]
    headers = {'User-Agent': random.choice(user_agents)}

    try: site_request = requests.get(site_url, headers=headers)
    except: return False
    else: return BeautifulSoup(site_request.text, 'html.parser')

def text_parser(text, index, split_str=None, slice=2):
    """Parses text from details page of product."""

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

    lprint(ctx, f"Fetched product data: {format(product_code)}")
    return liquor_data


# ========== Commands
@bot.command(aliases=['setup', 'dm', 'message'])
async def new(ctx, *args):
    """Send message to user."""

    await ctx.message.author.send("Hello!")
    lprint(ctx, f"Send DM: {ctx.message.author.name}")

@bot.command(aliases=['inv', 'Inv', 'Check', 'check', 'i', 'I'])
async def inventorycheck(ctx, *product_code):
    """Gets product data by store code(s)."""

    product_code = await check_use_ac(ctx, product_code)
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
    lprint(ctx, f"Inventory Check: {format(product_code)}")

@bot.command(aliases=['Codediff', 'dif', 'Diff', 'd', 'D'])
async def codediff(ctx, *product_code):
    """Checks if codes are in active_codes."""

    for i in product_code:
        if i in active_codes[ctx.message.author.name]:
            # Will show what group the match was in
            await ctx.send(f"Match in group {active_codes[ctx.message.author.name].index(i) / 5 + 1:.0f}: {i}")

@bot.command(aliases=['Add', 'add', 'addcode', 'Addcode', 'a', 'A'])
async def codeadd(ctx, *product_code):
    """Add codes to active_codes."""

    product_code = remove_dupes(product_code)
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
    lprint(ctx, f"Code added: {format(product_code)}")

@bot.command(aliases=['remove', 'Remove', 'r', 'R'])
async def coderemove(ctx, *product_code):
    """Removes active codes."""

    global active_codes

    if not check_active(ctx):
        await ctx.send("No active codes")
        return

    product_code = await check_use_ac(ctx, product_code)
    removed_codes, new_codes = [], []
    for i in active_codes[ctx.message.author.name]:
        # Skips adding code to active_codes if matched code that needs to be removed.
        if i in product_code:
            removed_codes.append(i)
            continue
        new_codes.append(i)
    active_codes[ctx.message.author.name] = new_codes.copy()

    await ctx.send(f"Removed codes: {', '.join(removed_codes)}")
    lprint(ctx, f'Removed codes: {format(product_code)}')

@bot.command(aliases=['Clear', 'clear', 'cc', 'Cc', 'CC'])
async def codeclear(ctx, *args):
    """Clears active_codes."""

    global active_codes

    if args: return

    active_codes[ctx.message.author.name].clear()
    await ctx.send("Cleared active codes")
    lprint(ctx, 'Cleared codes')

@bot.command(aliases=['Code', 'Codes', 'codes', 'c', 'C'])
async def codeget(ctx, group=''):
    """Fetches current active codes."""

    if not check_active(ctx):
        await ctx.send("No active codes")
        return

    # Get specified number group
    start_range, end_range = 0, None
    try:
        start_range = int(group) * 5 - 5
        end_range = start_range + 5
    except: pass

    # Prints out all active_codes in groups of 5 or just a specific group.
    text, counter = '', 0
    for i in active_codes[ctx.message.author.name][start_range:end_range]:
        if group and counter % 5 == 0: text += f"**Group {group}** -----\n"
        elif counter == 0: text += '**Group 1** ----------\n'
        elif counter % 5 == 0 and counter > 1:
            text += f'**{(counter / 5) + 1:.0f}** ----------\n'
        counter += 1
        text += f'{i}\n'

    await ctx.send(f"**Active Codes:**\n{text}")
    await ctx.send("----------END----------")
    lprint(ctx, 'Fetched active codes')

# ===== Photo
def get_photos(code):
    """Finds files with code in name, e.g. 7221.jpg, 7221-2.jpg"""

    files = []
    for i in os.listdir(box_photos_path):
        if code in i:
            files.append(i)

    return files

@bot.command(aliases=['box', 'Box', 'Boxphoto', 'Boxpicture', 'b', 'B', 'photo', 'Photo', 'picture', 'Picture''p', 'P'])
async def boxphoto(ctx, *product_code):
    """Gets photo of liquor box from code."""

    product_code = await check_use_ac(ctx, product_code)
    await ctx.send(f"***Checking Inventory and Fetching Images...***")
    product_data = get_product_data(product_code)

    if not product_data:
        await ctx.send("No inventory data available. Double check all codes.")
        return False

    async def create_embed(i, file_path=None, multiple=False):
        embed = discord.Embed()
        try: file = discord.File(f"{box_photos_path}/{file_path}", filename=f"{file_path}")
        except:  # If no matching image found for code.
            embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"*Pack:* **__{i['Pack']}__** | *On-hand:* **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`\nImage: Not Found", inline=False)
            await ctx.send(embed=embed)
        else:
            # If product has multiple photos, only first embed of product will show details.
            if multiple:
                embed.set_image(url=f"attachment://{file_path}")
                embed.add_field(name=f"{i['Name']}", value=f"Image: {file_path[:-4]}", inline=False)
                await ctx.send(file=file, embed=embed)
                return

            embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"*Pack:* **__{i['Pack']}__** | *On-hand:* **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`\nImage: {file_path[:-4]}", inline=False)
            embed.set_image(url=f"attachment://{file_path}")
            await ctx.send(file=file, embed=embed)

    for product in product_data:
        # Embed changes depending on if file found.
        filenames = get_photos(product['Code'])
        # Create embed with details even if no photo found
        if not filenames:
            await create_embed(product)
            continue

        if len(filenames) > 1:
            # If product has multiple images, first embed will show details only.
            await create_embed(product, filenames[0])
            for filename in filenames[1:]:
                await create_embed(product, filename, multiple=True)
        else: await create_embed(product, filenames[0])

    lprint(ctx, f'Fetched inventory+photo: {format(product_code)}')

@bot.command(aliases=['Boxphotoonly', 'photoonly', 'Photoonly', 'bp', 'Bp'])
async def boxphotoonly(ctx, *product_code):
    """Fetches image of box from product_code if exists."""

    product_code = await check_use_ac(ctx, product_code)
    files, no_matches = [], []
    for i in product_code:
        if filenames := get_photos(i):
            files.extend(filenames)
        else: no_matches.append(i)

    for filename in files:
        try: file = discord.File(f"{box_photos_path}/{filename}", filename=f"{filename}")
        except: pass
        else: await ctx.send(f'{filename[:-4]}', file=file)

    # Prints out codes that had no corresponding images.
    await ctx.send(f"No images for: {', '.join(no_matches)}")

@bot.command(aliases=['Boxupload', 'bu', 'Bu', 'upload', 'Upload', 'u', 'U'])
async def boxphotoupload(ctx, product_code):
    """Upload new photo of box and set filename."""

    try: product_code = str(int(product_code))
    except:
        await ctx.send("Please try again with corresponding product code")
        return

    # No duplicate filenames
    new_filename = f'{box_photos_path}/{product_code}-{random.randint(1, 10)}.jpg'
    for i in range(100):
        if os.path.isfile(new_filename):
            new_filename = f'{box_photos_path}/{product_code}-{random.randint(1, 10)}.jpg'

    # Saves with code as filename. e.g. 7221.jpg
    for attachment in ctx.message.attachments:
        await attachment.save(new_filename)

    await ctx.send(f"Received new box photo for: {product_code}")

    # Rescales photo by 50%.
    image_rescale.rescale(f"{box_photos_path}/{product_code}.jpg", 50)

    lprint(ctx, f"New box photo: {box_photos_path}/{product_code}.jpg")

@bot.command(aliases=['Boxphotorename', 'br', 'Br', 'Boxrename', 'rename', 'Rename', 're', 'Re'])
async def boxphotorename(ctx, product_code, new_code):
    """Rename photo."""

    # E.g. rename 7222 7221
    try: os.rename(f"{box_photos_path}/{product_code}.jpg", f"{box_photos_path}/{new_code}.jpg")
    except:
        await ctx.send("Error renaming image.")
        return
    await ctx.send(f"Image Renamed: {product_code}.jpg > {new_code}.jpg")
    lprint(ctx, f"Image Renamed: {product_code}.jpg > {new_code}.jpg")


# ===== Extra
@bot.command(aliases=['?'])
async def shortcuts(ctx):
    """Custom help page."""

    await ctx.send("""```
Command     - Description, example
c, codes    - Show current active codes
a, add      - Add active codes, a 7221, a 7221 6660 982
r, remove   - Remove active codes, r 6660, r 7221 6660
d, diff     - Check if code in active codes, d 7221, d 7221 982
i, inv      - Show inventory data, i 7221, i 7221 6660, i codes, i c
b, box      - Show inventory data with photo of boxes
bp          - Show only photo of boxes, bp 7221, bp 7221 6660, bp c 2
u, upload   - Upload new box image, u 7221
re, rename  - Rename image, re 7222 7221
```""")

@bot.command(aliases=['rbot', 'rebootbot', 'botrestart', 'botreboot'])
async def restartbot(ctx, now=''):
    """Restart this bot."""

    await ctx.send("***Rebooting Bot...*** :arrows_counterclockwise: ")
    lprint(ctx, "Restarting bot...")
    os.chdir('/')
    os.chdir(bot_path)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.command(aliases=['updatebot', 'botupdate', 'git', 'update'])
async def gitupdate(ctx):
    """Gets update from GitHub."""

    await ctx.send("***Updating from GitHub...*** :arrows_counterclockwise:")
    lprint(ctx, "Updating from GitHub")
    os.chdir(bot_path)
    os.system('git pull')
    await ctx.invoke(bot.get_command("restartbot"))

bot.run(TOKEN)
