import image_rescale, datetime, requests, discord, random, sys, os
from discord_components import DiscordComponents, Button, ButtonStyle,  Select, SelectOption, ComponentsBot
from file_read_backwards import FileReadBackwards
from bs4 import BeautifulSoup

__version__ = "2.1a"
__date__ = '2022/04/27'
__author__ = "DT"
__email__ = "dt01@pm.me"
__license__ = "GPL 3"
__status__ = "Development"

# ========== Variable & Funcs
bot_path = os.path.dirname(os.path.abspath(__file__))
bot_log_file = bot_path + '/liquor_log.txt'
box_photos_path = f'/home/{os.getlogin()}/Pictures/liquor_boxes'
box_photos_deleted_path = f'/home/{os.getlogin()}/Pictures/liquor_boxes_deleted'  # Where to move deleted photos
token_file = f'{os.getenv("HOME")}/keys/liquor_bot.token'
bot_channel_id = 988549339808952371
ctx = "liquor_bot.py"  # For logging

data_points = ['Name', 'Details', 'Code', 'Pack', 'Inventory', 'Ordered']
data_dict = {k:'N/A' for k in data_points}
# No Entry: Not exist | X: Exists but not on-hand | Check mark: On hand | F: Box found | S: Shelved
data_dict.update({'Icon': ':question:', 'Status': ''})
user_liquor_data = {'test_user': data_dict}  # Keep track of status of product found or shelved.
user_active_codes = {'test_user': ['7777777']}  # Each user gets own list of saved codes

def lprint(ctx, msg):
    """Prints and Logs events in file."""

    try: user = ctx.message.author
    except: user = ctx

    output = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ({user}): {msg}"
    print(output)

    # Logs output.
    with open(bot_log_file, 'a') as file:
        file.write(output + '\n')

def format(codes):
    """Formats codes for messages"""

    return ', '.join(codes)

def check_dict(key, input_dict):
    """Checks if user has a list in user_active_codes."""
    try: key = key.message.author.name
    except: pass
    try:
        _ = input_dict[key]
        return True
    except: return False

def check_codes_usable(input_codes):
    """Check if all codes are integers while preserving order."""

    codes, return_data = [], []
    if type(input_codes) is str: codes = [input_codes]
    try:
        for i in input_codes:
            return_data.append(str(int(i)))
        if type(codes) is str: return return_data[0]
        return return_data
    except: return False

def remove_dupes(input_list):
    """Removes duplicate codes while preserving order"""
    return sorted(set(input_list), key=lambda x: input_list.index(x))

async def check_use_ac(ctx, paramters):
    """Get codes or a group from user_active_codes if received right parameter."""

    user = ctx.message.author.name
    use_ac, list_index = False, 0
    for i in ['c', 'C', 'Code', 'code', 'Codes', 'codes']:
        if i in paramters: use_ac = True
    # When not using user_active_codes list
    if not use_ac: return remove_dupes(paramters)

    # Optionally specify code group, use codeget() to see groups.
    if len(paramters) == 2:
        # Need special case to fetch group 1 of codes
        if paramters[-1] == '1': return user_active_codes[user][:5]

        # Slices list up to extract the 5 specified codes of group.
        try: list_index = int(paramters[-1]) * 5 - 5
        except: await ctx.send("Could not get group.")
        else: return user_active_codes[user][list_index:list_index + 5 if list_index else len(user_active_codes[user])]
    else:
        try: return user_active_codes[user]
        except: return False

# ===== Web Scraper
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

def liquor_parser(product_code, user=None):
    """Parses data into dictionary."""

    # E.g. [{'Name': 'M & R Sweet Vermouth', 'Details': 'BACARDI USA INC, IMPORTED VERMOUTH, ITALIAN VERMOUTH ',
    #       'Pack': 6, 'Inventory': 8, 'Ordered': 12, etc...}
    return_data = data_dict.copy()
    try: return_data.update(user_liquor_data[user][product_code])
    except: pass
    return_data.update({'Name': product_code,'Code': product_code})

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

        if int(return_data['Inventory']) / int(return_data['Pack']) >= 1: return_data['Icon'] = ':white_check_mark:'
        else: return_data['Icon'] = ':x:'
    except: pass

    return return_data

def get_product_data(product_codes=None, user=None):
    """Fetches and parses product data."""

    liquor_data = []

    # Makes sure each code is usable first by converting to int and back.
    product_codes = check_codes_usable(product_codes)
    if not product_codes: return False

    for i in product_codes:
        liquor_data.append(liquor_parser(i, user))

    lprint(ctx, f"Fetched product data: {format(product_codes)}")
    return liquor_data


# ========== Discord
if os.path.isfile(token_file):
    with open(token_file, 'r') as file: TOKEN = file.readline()
else:
    print("Missing Token File:", token_file)
    sys.exit()
bot = ComponentsBot(command_prefix='', case_insensitive=True, help_command=None)

@bot.event
async def on_ready():
    lprint(ctx, "Bot Connected")
    await bot.wait_until_ready()
    bot_channel = bot.get_channel(bot_channel_id)
    await bot_channel.send(f':white_check_mark: **Bot PRIMED** {datetime.datetime.now().strftime("%X")}')

@bot.command(aliases=['setup', 'dm'])
async def new(ctx, *args):
    """Send message to user."""

    await ctx.message.author.send("Hello! Use `help` command for more info.")
    lprint(ctx, f"Sent DM: {ctx.message.author.name}")

@bot.command(aliases=['info', 'inv', 'inventory', 'i'])
async def inventorycheck(ctx, *product_codes):
    """Gets product data by store code(s)."""

    global user_liquor_data

    user = ctx.message.author.name
    product_codes = await check_use_ac(ctx, product_codes)
    await ctx.send(f"***Checking Inventory...***")
    product_data = get_product_data(product_codes, user)

    if not product_data:
        await ctx.send("No inventory data available.")
        return False

    if not check_dict(user, user_liquor_data):
        user_liquor_data.update({user: dict()})

    # Preserves 'Icon' value from user_liquor_data
    for i in product_data:
        for k, v in i.items():
            if 'Icon' in k:
                try: i['Icon'] = user_liquor_data[user][i['Code']]['Icon']
                except: pass

    embed = discord.Embed(title='Inventory')
    embed.add_field(name='Legend', value=f":white_check_mark: On-hand | :x: Not on-hand | :question: Unknown\n:regional_indicator_f: Box found | :regional_indicator_s: Shelved")
    for i in product_data:
        # Updates/adds to user_liquor_data
        try: user_liquor_data[user][i['Code']].update(i)
        except: user_liquor_data[user] |= {i['Code']: i}
        image_status = 'Not found'
        if get_photos(i['Code']): image_status = 'Available'

        embed.add_field(name=f"{i['Icon']} {i['Name']}", value=f"Pack: **__{i['Pack']}__** | On-hand: **__{i['Inventory']}__** | Ordered: {i['Ordered']}\nDetails: `{i['Code']}, {i['Details']}`\nImage: **{image_status}**", inline=False)

    await ctx.send(embed=embed)
    lprint(ctx, f"Inventory Check: {format(product_codes)}")

# ===== Box Status
async def status_updater(ctx, icon, status, product_codes):
    """Updates status of product, i.e. found, shelved."""

    global user_liquor_data

    user = ctx.message.author.name
    if not check_dict(ctx, user_liquor_data):
        user_liquor_data.update({user: dict()})

    for code in product_codes:
        try: user_liquor_data[user][code].update({'Icon': icon, 'Status': status, 'Code': code})
        except: user_liquor_data[user][code] = {'Icon': icon, 'Status': status, 'Code': code}

@bot.command(aliases=['f'])
async def found(ctx, *product_codes):
    """Update box status to shelved."""

    product_codes = await check_use_ac(ctx, product_codes)
    await status_updater(ctx, ':regional_indicator_f:', 'Found', product_codes)
    await ctx.send(f"Found: {format(product_codes)}")
    lprint(ctx, f"Found: {format(product_codes)}")

@bot.command(aliases=['s'])
async def shelved(ctx, *product_codes):
    """Update box status to shelved."""

    product_codes = await check_use_ac(ctx, product_codes)
    await status_updater(ctx, ':regional_indicator_s:', 'Shelved', product_codes)
    await ctx.send(f"Shelved: {format(product_codes)}")
    lprint(ctx, f"Shelved: {format(product_codes)}")

# ===== Saved Codes
@bot.command(aliases=['codes', 'c'])
async def codeget(ctx, group=''):
    """Fetches current saved codes."""

    user = ctx.message.author.name
    if not check_dict(ctx, user_active_codes):
        await ctx.send("No saved codes")
        return

    # Get specified number group
    list_index = 0
    try: list_index = int(group) * 5 - 5
    except: pass

    # Prints out all user_active_codes in groups of 5 or just a specific group.
    text, counter = '', 0
    for i in user_active_codes[user][list_index:list_index + 5 if list_index else len(user_active_codes[user])]:
        if group and counter % 5 == 0: text += f"**Group {group}** -----\n"
        elif counter == 0: text += '**Group 1** ----------------\n'
        elif counter % 5 == 0 and counter > 1:
            text += f'**{(counter / 5) + 1:.0f}** ----------\n'
        counter += 1

        status = ''
        try: status = user_liquor_data[user][i]['Status']
        except: pass
        text += f'{i} {status}\n'

    await ctx.send(f"**Saved Codes:**\n{text}")
    await ctx.send("----------END----------")
    lprint(ctx, 'Fetched saved codes')

@bot.command(aliases=['match'])
async def codematch(ctx, *product_codes):
    """Checks if codes are in user_active_codes."""

    for i in product_codes:
        if i in user_active_codes[ctx.message.author.name]:
            # Will show what group the match was in
            await ctx.send(f"Match in group {user_active_codes[ctx.message.author.name].index(i) / 5 + 1:.0f}: {i}")

@bot.command(aliases=['add', 'a'])
async def codeadd(ctx, *product_codes):
    """Add codes to user_active_codes."""

    product_codes = remove_dupes(product_codes)
    global user_active_codes

    user = ctx.message.author.name
    # So each user can have their own set of codes.
    if user not in user_active_codes:
        user_active_codes[user] = []

    # Makes sure all codes are numbers and removes duplicate codes.
    try:
        new_codes = []
        for i in product_codes:
            if i not in user_active_codes[user]:
                new_codes.append(str(int(i)))
        user_active_codes[user].extend(new_codes)
    except:
        await ctx.send("Not all were usable codes")
        return

    await ctx.send(f"Added codes: {format(product_codes)}")
    await ctx.invoke(bot.get_command("codeget"))
    lprint(ctx, f"Code added: {format(product_codes)}")

@bot.command(aliases=['remove', 'r'])
async def coderemove(ctx, *product_codes):
    """Removes saved codes."""

    global user_active_codes

    if not check_dict(ctx, user_active_codes):
        await ctx.send("No saved codes")
        return

    product_codes = await check_use_ac(ctx, product_codes)
    removed_codes, new_codes = [], []
    for i in user_active_codes[ctx.message.author.name]:
        # Skips adding code to user_active_codes if matched code that needs to be removed.
        if i in product_codes:
            removed_codes.append(i)
            continue
        new_codes.append(i)
    user_active_codes[ctx.message.author.name] = new_codes.copy()

    await ctx.send(f"Removed codes: {format(removed_codes)}")
    lprint(ctx, f'Removed codes: {format(product_codes)}')

@bot.command(aliases=['clear', 'cc'])
async def codeclear(ctx, *args):
    """Clears user_active_codes."""

    global user_active_codes, user_liquor_data

    if args: return

    user_liquor_data.clear()
    try: user_active_codes[ctx.message.author.name].clear()
    except: pass
    await ctx.send("Cleared saved codes")
    lprint(ctx, 'Cleared codes')


# ===== Photo
def get_photos(code):
    """Finds files with code in name, e.g. 7221.jpg, 7221-2.jpg"""

    files = []
    for i in os.listdir(box_photos_path):
        i_code = i.split('.')[0]
        # Gets code from filenames like 7221-9.jpg
        try: i_code = i_code.split('-')[0]
        except: pass
        if i_code == code:
            files.append(i)

    return files

@bot.command(aliases=['box', 'b', 'photo', 'p'])
async def boxphoto(ctx, *product_codes):
    """Gets photo of liquor box from code."""

    product_codes = await check_use_ac(ctx, product_codes)
    await ctx.send(f"***Checking Inventory and Fetching Images...***")
    product_data = get_product_data(product_codes)

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

    await ctx.send("**Finished**")
    lprint(ctx, f'Fetched inventory+photo: {format(product_codes)}')

@bot.command(aliases=['bp'])
async def boxphotoonly(ctx, *product_codes):
    """Fetches image of box from product_codes if exists."""

    product_codes = await check_use_ac(ctx, product_codes)
    files, no_matches = [], []
    for i in product_codes:
        if filenames := get_photos(i):  # Returns list if files found
            files.extend(filenames)
        else: no_matches.append(i)

    for filename in files:
        try: file = discord.File(f"{box_photos_path}/{filename}", filename=f"{filename}")
        except: pass
        else: await ctx.send(f'{filename[:-4]}', file=file)

    # Prints out codes that had no corresponding images.
    if no_matches: await ctx.send(f"No images for: {format(no_matches)}")
    else: await ctx.send("**Finished**")
    lprint(ctx, f"Fetched box photo: {format(product_codes)}")

@bot.command(aliases=['boxupload', 'bu', 'upload', 'u'])
async def boxphotoupload(ctx, product_codes):
    """Upload new photo of box and set filename."""

    # Check if code is a number and message has attachment
    product_codes = check_codes_usable([product_codes])
    if not ctx.message.attachments or not product_codes:
        await ctx.send("Please try command again with code and attached photo.")
        return
    else: product_codes = product_codes[0]

    # Makes sure no duplicate filenames
    new_filename = f"{product_codes}-{random.randint(1, 10)}.jpg"
    for i in range(100):
        if os.path.isfile(f"{box_photos_path}/{new_filename}"):
            new_filename = f'{product_codes}-{random.randint(1, 10)}.jpg'
    file_path = f'{box_photos_path}/{new_filename}'

    # Saves with code as filename. e.g. 7221-6.jpg
    for attachment in ctx.message.attachments:
        await attachment.save(file_path)
    # Rescales photo by 50%.
    image_rescale.rescale(file_path, 50)

    await ctx.send(f"New upload: {new_filename}")
    lprint(ctx, f"New box photo: {new_filename}")
    await ctx.invoke(bot.get_command("boxphoto"), product_codes)

@bot.command(aliases=['boxrename', 'br', 'rename'])
async def boxphotorename(ctx, product_codes, new_code):
    """Rename photo."""

    # E.g. rename 7222 7221
    try: os.rename(f"{box_photos_path}/{product_codes}.jpg", f"{box_photos_path}/{new_code}.jpg")
    except:
        await ctx.send("Error renaming photo.")
        return
    await ctx.send(f"Image Renamed: {product_codes}.jpg > {new_code}.jpg")
    lprint(ctx, f"Image Renamed: {product_codes}.jpg > {new_code}.jpg")

@bot.command(aliases=['bd', 'bpd'])
async def boxphotodelete(ctx, photo_name):
    """Moves photo to liquor_boxes_deleted folder."""

    try:
        # os.rename does actually move file.
        os.rename(f"{box_photos_path}/{photo_name}.jpg", f"{box_photos_deleted_path}/{photo_name}.jpg")
        await ctx.send(f"Deleted: {photo_name}")
        lprint(ctx, f"Deleted: {photo_name}")
    except: await ctx.send(f"Error deleting or file not exist: {photo_name}")

@bot.command(hidden=True, aliases=['pd'])
async def photodupes(ctx):
    """If code has more than 1 corresponding photo, will be moved to another folder for review."""

    files, have_multiple = [], set()
    for i in os.listdir(box_photos_path):
        files.append(i)

    # Checks if there's multiple photos of same product (not duplicate files)
    for i in files:
        i = i.split('.')[0]
        try: i = i.split('-')[0]
        except: pass
        if len(get_photos(i)) > 1:
            have_multiple.add(i)
            os.rename(f"{box_photos_path}/{file}", f"/home/0n1udra/Pictures/dupes/{file}")

    if not have_multiple:
        await ctx.send("No duplicates found")
    else: await ctx.send(f"Files moved: {format(have_multiple)}")
    lprint(ctx, "Checked for duplicates")

# ===== Extra
@bot.command(aliases=['help', '?', 'alias', 'shortcuts'])
async def commands(ctx, *args):
    """Custom help page."""

    commands = [
    ['Recommend using bot in Direct Messages', 'Use `dm` command to have bot send you a private message.', 'So no confusion/conflicts when multiple people are using the bot. (Unless you want to share with the class, feel free too)'],
    ['Saving product codes', 'Save/remove codes with `add`/`remove` commands. Use `codes` to see all saved codes (in groups of 5).', '`a 7221` (Save code), `r c 1` (Remove group 1 codes), `c 1` (Show group 1)'],
    ['Using saved codes for commands', 'Some commands can use saved codes (or a group).', '`i c` (Get info for all saved codes), `b c 1` (Get info + box photo for group 1)'],
    ['Shortcut, Command', 'Description.', 'Usage examples'],
    ['c, codes', 'Show current codes saved.', '`c`, `c 1`'],
    ['a, add / r, remove / cc, clear', 'Add/remove/clear saved codes.', '`a 7221 6214`, `r c 1`, `cc`'],
    ['m, match', 'Check if in saved codes.', '`m 7221 6660`'],
    ['i, info, inventory', 'Show inventory info for codes (name, how many on-hand, etc).', '`i 7221 6660`, `i c`'],
    ['f, found & s, shelved', 'Update box status (found box, shelved product).', '`f 7221`, `s 7221 6660`, `s c 1`'],
    ['b, box', 'Show inventory info with box photo.', '`b 7221`, `b c 1`'],
    ['bp, boxphoto', 'Show box photo only', '`bp 7221 6660`, `bp c 1`'],
    ['bu, u, boxphotoupload', 'Upload box photo for a code. (Only one code and one photo only).', '`u 7221` + attached photo'],
    ['br, boxphotorename', "Rename photo. (Keep the '-X' portion when renaming. Do NOT include extension e.g. .jpg).", '`br 7222 7221`, `br 6215-9 6214-9`'],
    ['bd, boxphotodelete', 'Delete photo. (One code only).', '`bd 7221`, `bd 6214-9`'],
    ['NOTE: Commands are case insensitive', "I.e. capitalization (or even full caps or mixed) does not matter.", '`cc`, `Cc`, `cC`, `CC` (all the same)']

    ]

    embed = discord.Embed(title='Commands')
    for c in commands: embed.add_field(name=c[0], value=f"{c[1]}\n{c[2]}", inline=False)
    await ctx.send(embed=embed)
    lprint(ctx, "Help page")

@bot.command(hidden=True, aliases=['rbot'])
async def restartbot(ctx, now=''):
    """Restart this bot."""

    await ctx.send("***Rebooting Bot...*** :arrows_counterclockwise: ")
    lprint(ctx, "Restarting bot...")
    os.chdir('/')
    os.chdir(bot_path)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.command(hidden=True, aliases=['blog'])
async def botlog(ctx, lines=5):
    """Show bot log."""

    if not os.path.isfile(bot_log_file):
        await ctx.send("**Error:** Problem fetching data. File may be empty or not exist")
        lprint(ctx, "ERROR: Issue getting bog log data.")
        return

    line_count = sum(1 for line in open(bot_log_file))

    with FileReadBackwards(bot_log_file) as file:
        i = total = 0
        # Stops loop at user set limit, if file has no more lines, or at hard limit (don't let user ask for 999 lines of log).
        while i < lines and total < line_count and total <= 100:
            total += 1
            line = file.readline()
            try: await ctx.send(f"_({line.split(']', 1)[0][1:]})_ **{line.split(']', 1)[1].split('):', 1)[0][2:]}**: {line.split(']', 1)[1].split('):', 1)[1][1:]}")
            except: continue
            if not line.strip(): continue  # Skip blank/newlines.
            i += 1

    await ctx.send("-----END-----")
    lprint(ctx, f"Fetched Bot Log: {lines}")

@bot.command(hidden=True)
async def gitupdate(ctx):
    """Gets update from GitHub."""

    await ctx.send("***Updating from GitHub...*** :arrows_counterclockwise:")
    lprint(ctx, "Updating from GitHub")
    os.chdir(bot_path)
    os.system('git pull')
    await ctx.invoke(bot.get_command("restartbot"))

bot.run(TOKEN)
