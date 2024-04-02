from anthropic import Anthropic
import pymongo
from pymongo import MongoClient
import sys
import os
import json
from twitchio.ext import commands
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()
TWITCH_KEY = os.getenv('TWITCH_KEY')
ANTHROPIC_KEY = os.getenv('ANTHROPIC_KEY')

#init baza 
connstring = "mongodb://192.168.100.200:27017/?tls=false"
db_name = "donjohn"
collection_name="TwitchMessages"
dbClient = MongoClient(connstring)
db = dbClient[db_name]
collection= db[collection_name]

#init anthropic
aiClient = Anthropic(
    api_key=ANTHROPIC_KEY
)
MODEL_NAME = "claude-3-sonnet-20240229" # claude-3-sonnet-20240229 claude-3-haiku-20240307 claude-3-opus-20240229 (HAIKU - TANI, SONNET - LEKKO MNIEJ TANI, OPUS - W CHUJ DROGI)

assistant = {
    "role":"assistant",
    "content":"Okay, i'll reply accordingly, using your provided description!"
}


#USEFUL FUNKCJE KTORYCH BRAKUJE

def stripcommand(message): #usuwa $donjohn albo inne komendy ze stringa
    slowa = message.split(' ', 1)
    wiadomoscStripped = ''.join(slowa[1:])
    return wiadomoscStripped


#funkcje główne
def czytaj_json(id):
    filejson = open('prompt.json')
    config = json.load(filejson)
    return config[id][0]

#wyslanie zapytania do api anthropic, wiadomosc, rola - osobowość którą ma obrać (zdefiniowana w prompt.json), i opcjonalnie kontekst
def send_to_ai(msg,rola,kontekst=None): 
    usermessage = { 
    "role":"user",
    "content":msg
    }
    system_message = czytaj_json(rola)
    if kontekst: 
        system_message += kontekst+"\n</context>\n"
    else:
        system_message += "No context</context>\n"
    reply = aiClient.messages.create(
        model=MODEL_NAME,
        max_tokens=300,
        system=system_message,
        messages=[usermessage]
    ).content[0].text
    return reply
def send_to_db(dane):
    data = datetime.now()
    data = str(data)
    dane.update({"data": data}) #dodaj date zapisu
    r = collection.insert_one(dane)
    print(f"MongoDB commit id {r.inserted_id}")

def get_user_message_history(user):
    historia = ''
    filter={
    '$or': [
        {
            'od': 'aaxile'
        }, {
            '$and': [
                {
                    'od': 'donjohn_bot'
                }, {
                    'odpowiada_dla': user
                }
            ]
        }
    ]
    }
    sort=list({
        'data': -1
    }.items())
    limit=6
    result = dbClient['donjohn']['TwitchMessages'].find(
    filter=filter,
    sort=sort,
    limit=limit
    )
    for document in result:
        msg = document['wiadomość']
        msg = stripcommand(msg)
        od = document['od']
        calosc = f"<user>{od}</user><text>{msg}</text>\n"
        historia+=calosc
    return historia




#init twitch
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TWITCH_KEY, prefix='$', initial_channels=['aaxile','donhoman'])
    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
    async def event_message(self, message):
        if message.echo:
            # #zapisuje do bazy też swoje wiadomości, i ignoruje je potem, żeby sie nie zapętlił
            # payload = {"od":"donjohn_bot", "wiadomość":message.content, "kanał":message.channel.name} 
            # send_to_db(payload)
            return
        payload = {"od":message.author.name, "wiadomość":message.content, "kanał":message.channel.name}
        send_to_db(payload)
        await self.handle_commands(message)
    # komendy ---------------------------------------------------

    # funkcja komendy
    # 1 strip $<nazwaKomendy> z wiadomosci funkcją stripcommand(), zwraca sam tekst
    # 2 send_to_ai(tekst, osobowość) - osobowości z jakimi ma odpowiadać zdefiniowane są ręcznie w prompt.json
    # 3 send_to_db(autor, wiadomosc, kanał) zapisuje w mongo z kanałem na którym wysłano wiadomość

    @commands.command()
    async def dj(self, ctx: commands.Context):
        wiadomosc = stripcommand(ctx.message.content)
        kontekst = get_user_message_history(ctx.message.author.name)
        odp = send_to_ai(wiadomosc, 'DonJohn', kontekst)
        await ctx.send(odp)
        #zapisz odpowiedz bota do db, z polem odpowiada_dla, żeby potem mieć kontekst per user
        payload = {"od":"donjohn_bot", "wiadomość":odp, "kanał":ctx.channel.name, "odpowiada_dla":ctx.message.author.name}
        send_to_db(payload)

    @commands.command()
    async def google(self, ctx: commands.Context):
        wiadomosc = stripcommand(ctx.message.content)
        kontekst = get_user_message_history(ctx.message.author.name)
        odp = send_to_ai(wiadomosc, 'AI_normal', kontekst)
        await ctx.send(odp)
        payload = {"od":"google_bot", "wiadomość":odp, "kanał":ctx.channel.name, "odpowiada_dla":ctx.message.author.name}
        send_to_db(payload)
    @commands.command()
    async def s(self, ctx: commands.Context):
        wiadomosc = stripcommand(ctx.message.content)
        odp = send_to_ai(wiadomosc, 'slaski')
        await ctx.send(odp)
        # send_to_db(ctx.author.name,ctx.message.content,ctx.channel)

bot=Bot()
bot.run()

# dbClient.close() - to chyba musi byc ale nie wiem kiedy ani gdzie

