# -*- coding: utf-8 -*-

from marvinbot.utils import localized_date, get_message
from marvinbot.handlers import CommandHandler, CallbackQueryHandler
from marvinbot.plugins import Plugin
from marvinbot.models import User

from bs4 import BeautifulSoup

from collections import OrderedDict

import logging
import re
import requests
import ctypes
import bs4
import time
import datetime
import time

log = logging.getLogger(__name__)

last = []

class MarvinBotPelotaPlugin(Plugin):
    def __init__(self):
        super(MarvinBotPelotaPlugin, self).__init__('marvinbot_pelota_plugin')
        self.bot = None

    def get_default_config(self):
        emoji = {
            "Estrellas Orientales":"⭐",
            "Aguilas Cibaeñas":"🦅",
            "Gigantes del Cibao":"🐴",
            "Leones del Escogido":"🦁",
            "Escogido":"🦁",
            "Tigres del Licey":"🐯",
            "Toros del Este":"🐮"
        }
        countries = {
            "DOMINICANA":"🇩🇴",
            "CUBA":"🇨🇺",
            "PUERTO RICO":"🇵🇷",
            "VENEZUELA":"🇻🇪",
            "MÉXICO":"🇲🇽",
            "DOM":"🇩🇴",
            "CUB":"🇨🇺",
            "PRI":"🇵🇷",
            "VEN":"🇻🇪",
            "MEX":"🇲🇽"
        }
        return {
            'short_name': self.name,
            'enabled': True,
            'base_url': 'http://lidomwidgets.digisport.com.do/Estadisticas/Standings/Standings',
            'base_url_dashboard': 'http://estadisticas.lidom.com/Estadisticas/Inicio/Pizarra',
            'base_caribbean_url': 'https://www.seriecaribe.org',
            'base_series_url': 'http://seriedelcaribeapp.info/api/digimetrics/score',
            'emoji': emoji,
            "countries": countries,
            'timer': 15*60
        }

    def configure(self, config):
        self.config = config
        pass

    def setup_handlers(self, adapter):
        self.bot = adapter.bot
        self.add_handler(CommandHandler('pelota', self.on_pelota_command, command_description='Dominican Republic Baseball Standings.'))
        self.add_handler(CommandHandler('pizarra', self.on_pizarra_command, command_description='Dominican Republic Baseball Dashboard.'))
        self.add_handler(CommandHandler('caribe', self.on_caribbean_command, command_description='Caribbean Series Standings.'))
        self.add_handler(CommandHandler('serie', self.on_series_command, command_description='Caribbean Series Dashboard.'))

    def setup_schedules(self, adapter):
        pass

    # Pelota
    def stats_parse(self, response_text):
        r = OrderedDict()
        html_soup = BeautifulSoup(response_text, 'html.parser')

        for tr in html_soup.tbody.find_all('tr'):
            team = tr.td.a.text.strip()

            # J G P Pct Dif
            r[team] = [td.text.strip() for td in tr.find_all('td')[1:]]

        return r

    def stats_http(self, temporada="", etapa="SR"):
        r = None

        with requests.Session() as s:
            data = {}
            data["Etapa"] = etapa
            if temporada:
                data["Temporada"] = temporada 

            response = s.post(self.config.get('base_url'), data=data, timeout=60)
            r = self.stats_parse(response.text)

        return r

    def stats_msg(self, data, title):
        msg = "*{}*\n\n".format(title)

        for team in data:
            msg += "{} *{}*\n*J:* {}, *G:* {}, *P:* {}, *Pct:* {}, *Dif:* {}\n".format(self.config.get("emoji").get(team), team, *data[team])
        
        return msg

    # Pizarra
    def dashboard_parse(self, response_text):
        def getnum(txt):
            if not txt:
                pass
            rgx = re.compile(".*(\d+)\.png")
            return rgx.search(txt).group(1)

        dashboard = []
        html_soup = BeautifulSoup(response_text, 'html.parser')

        for table in html_soup.find_all('table', class_='PizarraPequena'):
            game = OrderedDict()
            teams = []
            results = []
        
            game['stadium'] = re.sub(' +',' ',table.thead.tr.th.a.text.strip().replace("\r\n","").replace("@",""))
        
            for tr in table.tbody:
                if type(tr) is bs4.element.Tag:
                    diamante = tr.find(class_='Diamante')
                    if diamante:
                        span = [x.text.strip() for x in diamante.find_all('span')]
                        game['inning'] = " ".join(span)
                    elif 'inning' not in game:
                        game['inning'] = "FINAL"
                        
                    equipo = tr.find('td', class_='Equipo2')
                    if equipo and equipo.div.img.get('alt') is not '':
                            teams.append(equipo.div.img.get('alt'))
                    else:
                        equipo = tr.find('td', class_='Equipo')
                        if equipo and equipo.img.get('alt') is not '':
                            teams.append(equipo.img.get('alt'))
        
                    result = [td.text.strip() for td in tr.find_all('td', class_='EX')]
                    if result:
                        results.append(result)
        
                    img = [getnum(i['src']) for i in tr.find_all('img') if not i['alt']]
                    if len(img) == 3:
                        game['obs'] = img

                    err = [td.text.strip() for td in tr.find_all('td', class_='EX2')]
                    if err:
                        game['err'] = err

            game['teams'] = teams
            game['results'] = results
        
            dashboard.append(game)
        
        return dashboard

    def dashboard_http(self):
        r = None

        with requests.Session() as s:
            response = s.post(self.config.get('base_url_dashboard'), timeout=60)
            r = self.dashboard_parse(response.text)

        return r

    def dashboard_msg(self, dashboard):
        msg = ""
        
        for game in dashboard:
            if 'err' in game:
                msg += "Estadio: *{}*\n{}\n".format(game['stadium'], " ".join(game['err']))
                msg += "{} vs {}\n".format(self.config.get("emoji").get(game['teams'][0]),self.config.get("emoji").get(game['teams'][1]))
            else:
                msg += "Estadio: *{}*\n{}\n\n---- R H E\n".format(game['stadium'], game['inning'])
                msg += "{} {} {} {}\n".format(self.config.get("emoji").get(game['teams'][0]), *game['results'][0])
                msg += "{} {} {} {}\n".format(self.config.get("emoji").get(game['teams'][1]), *game['results'][1])
                if 'obs' in game:
                    msg += "O: {}, B: {}, S: {}\n".format(*game['obs'])
            msg += "-"*20 + "\n"

        return msg

    # Caribe
    def caribbean_parse(self, response_text):
        r = OrderedDict()
        html_soap = BeautifulSoup(response_text, 'html.parser')
        stading = html_soap.find('table', class_='table-standings')
        
        for tr in stading.tbody.find_all('tr'):
            team = tr.find('h6').text.strip()
            r[team] = [td.text.strip() for td in tr.find_all('td')[1:]]

        return r

    def caribbean_http(self):
        r = None

        with requests.Session() as s:
            response = s.get(self.config.get('base_caribbean_url'), timeout=90)
            r = self.caribbean_parse(response.text)

        return r

    def caribbean_msg(self, data):
        msg = "*Serie del Caribe*\n\n"

        for team in data:
            msg += "{} *{}*\n*G:* {}, *P:* {}, *%:* {}, *Dif:* {}\n".format(self.config.get("countries").get(team), team, *data[team])
        
        return msg

    # Serie
    def series_parse(self, response):
        dashboard = []
        
        for game in response.json():
            g = OrderedDict()
            
            g['date'] = game['dateGame']
            g['status'] = game['status']['status']
        
            g['inning'] = game['inning']
            g['part'] = "Alta" if 'A' == game['part'].strip() else "Baja"
        
            g['obs'] = [game['outs'], game['balls'], game['strikes']]
        
            g['teams'] = [game['visitor']['name'].upper(), game['local']['name'].upper()]
            g['results'] = [
                [game['visitorBoard']['r'], game['visitorBoard']['h'], game['visitorBoard']['e']],
                [game['localBoard']['r'], game['localBoard']['h'], game['localBoard']['e']]
                ]
        
            dashboard.append(g)

        return dashboard

    def series_http(self):
        r = None

        headers = {
            "Authorization": "Basic bce4c0a9182d4d534c228e11e6c03ec3:JU1sb7c7FAUoYgU/MQROzy5gkOOTgZChx4jWlzjfL/o=:2018-02-04T03:01:37.465Z"
        }

        d = datetime.date.today() - datetime.timedelta(1) if int(time.strftime("%H")) < 9 else datetime.date.today()
       
        payload = {'date':  d.strftime("%a %b %d %Y")}

        with requests.Session() as s:
            response = s.get(self.config.get('base_series_url'), timeout=90, headers=headers, params=payload)
            r = self.series_parse(response)

        return r

    def series_msg(self, dashboard):
        msg = ""
        
        for game in dashboard:
            msg += "- {}\n{} {}\n\n---- R H E\n".format(game['status'], game['part'], game['inning'])
            msg += "{} {} {} {}\n".format(self.config.get("countries").get(game['teams'][0]), *game['results'][0])
            msg += "{} {} {} {}\n".format(self.config.get("countries").get(game['teams'][1]), *game['results'][1])
               
            msg += "O: {}, B: {}, S: {}\n".format(*game['obs'])
            msg += "-"*20 + "\n"

        return msg


    # Commands
    def on_pizarra_command(self, update, *args, **kwargs):
        global last
        message = get_message(update)
        last = [x for x in last if x['date'] + self.config.get("timer") > time.time()]
        old_message = next((x for x in last if x['chat_id'] == message.chat_id), None)

        try:      
            data = self.dashboard_http()
            msg = self.dashboard_msg(data)
        except Exception as err:
            log.error("Pelota error: {}".format(err))
            msg = "❌ Error occurred getting the dashboard."
            self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
            return

        if old_message and old_message['date'] + self.config.get("timer") > time.time():
            msg_update = "{}\n__updated at {}__\n".format(msg, datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S"))
            self.adapter.bot.editMessageText(chat_id=message.chat_id, text=msg_update, message_id=old_message['message_id'], parse_mode='Markdown', disable_web_page_preview = True)

            msg_replay = "#Pizarra updated successfully!"
            self.adapter.bot.sendMessage(chat_id=message.chat_id, reply_to_message_id=old_message['message_id'], text=msg_replay, parse_mode='Markdown', disable_web_page_preview = True)
        else:
            last_message = self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
            if old_message:
                last.remove(old_message)
            last.append({'date': time.time(), 'chat_id': message.chat_id, 'message_id': last_message.message_id})

    def on_pelota_command(self, update, *args, **kwargs):
        message = get_message(update)
        dashboard = kwargs.get('pizarra', False)
        
        msg = "❌ Season not found."

        try:
            year = ""
            cmd_args = re.sub('—\w*', '', message.text).split(" ")

            if len(cmd_args) > 1:
                year = cmd_args[1]
    
            data = self.stats_http(temporada=year)
            if data:
                msg = self.stats_msg(data, "Serie Regular")
    
            data = self.stats_http(temporada=year, etapa="RR")
            if data:
                msg += "\n"
                msg += self.stats_msg(data, "Serie Semifinal")
    
            data = self.stats_http(temporada=year, etapa="SF")
            if data:
                msg += "\n"
                msg += self.stats_msg(data, "Serie Final")
    
        except Exception as err:
            log.error("Pelota error: {}".format(err))
            msg = "❌ Error."

        self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)

    def on_caribbean_command(self, update, *args, **kwargs):
        message = get_message(update)
        dashboard = kwargs.get('pizarra', False)

        try:
            data = self.caribbean_http()
            msg = self.caribbean_msg(data)
        except Exception as err:
            log.error("Pelota error: {}".format(err))
            msg = "❌ Error."

        self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)

    def on_series_command(self, update, *args, **kwargs):
            global last
            message = get_message(update)
            last = [x for x in last if x['date'] + self.config.get("timer") > time.time()]
            old_message = next((x for x in last if x['chat_id'] == message.chat_id), None)
    
            try:      
                data = self.series_http()
                msg = self.series_msg(data)
            except Exception as err:
                log.error("Pelota error: {}".format(err))
                msg = "❌ Error occurred getting the dashboard."
                self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
                return
    
            if old_message and old_message['date'] + self.config.get("timer") > time.time():
                msg_update = "{}\n__updated at {}__\n".format(msg, datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S"))
                self.adapter.bot.editMessageText(chat_id=message.chat_id, text=msg_update, message_id=old_message['message_id'], parse_mode='Markdown', disable_web_page_preview = True)
    
                msg_replay = "#Serie updated successfully!"
                self.adapter.bot.sendMessage(chat_id=message.chat_id, reply_to_message_id=old_message['message_id'], text=msg_replay, parse_mode='Markdown', disable_web_page_preview = True)
            else:
                last_message = self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
                if old_message:
                    last.remove(old_message)
                last.append({'date': time.time(), 'chat_id': message.chat_id, 'message_id': last_message.message_id})
