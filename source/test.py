import requests, bs4
url = 'https://ice.liquor.nh.gov/public/default.asp?Category=inquiries&Service=prodfindconf'
session = requests.session().get(url)
#session.get(url)
keys = 'titos'
results = session.post(url, data={'REQ':keys})
soup = bs4.BeautifulSoup(results.text, 'html.parser')
tds = []
if table := soup.find_all('tr')[1]:
    for td in table.find_all('td'):
        try: int(td.contents[0].split(' ')[0])
        except: continue
        else: tds.append(td.contents[0])

    print(tds)

else:
    print("ERR")
    exit()

