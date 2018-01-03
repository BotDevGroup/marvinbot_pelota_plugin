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

log = logging.getLogger(__name__)


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
            "Toros del Este":"🐮",
        }
        return {
            'short_name': self.name,
            'enabled': True,
            'base_url': 'http://lidomwidgets.digisport.com.do/Estadisticas/Standings/Standings',
            'emoji': emoji
        }

    def configure(self, config):
        self.config = config
        pass

    def setup_handlers(self, adapter):
        self.bot = adapter.bot
        self.add_handler(CommandHandler('pelota', self.on_pelota_command, command_description='Dominican Republic Baseball Standings'))

    def setup_schedules(self, adapter):
        pass

    def html_parse(self, response_text):
        r = OrderedDict()
        html_soup = BeautifulSoup(response_text, 'html.parser')

        for tr in html_soup.tbody.find_all('tr'):
            team = tr.td.a.text.strip()

            # J G P Pct Dif
            data = []
            for td in tr.find_all('td')[1:]:
                data.append(td.text.strip())

            r[team] = data

        return r

    def http(self, temporada="", etapa="SR"):
        with requests.Session() as s:
            data = {}
            data["Etapa"] = etapa
            if temporada:
                data["Temporada"] = temporada 

            response = s.post(self.config.get('base_url'), data=data, timeout=60)
            r = self.html_parse(response.text)
            return r

    def make_msg(self, data, title):
        msg = "*{}*\n\n".format(title)

        for team in data:
            # msg += "{} *{}*\n--------- {}\n".format(self.config.get("emoji").get(team), team, "\t".join(data[team]))
            msg += "{} *{}*\n*J:* {}, *G:* {}, *P:* {}, *Pct:* {}, *Dif:* {}\n".format(self.config.get("emoji").get(team), team, *data[team])
        
        return msg

    def on_pelota_command(self, update, *args, **kwargs):
        message = get_message(update)
        msg = "❌ Season not found"

        try:
            year = ""
            cmd_args = message.text.split(" ")
            if len(cmd_args) > 1:
                year = cmd_args[1]

            data = self.http(temporada=year)
            if len(data) > 0:
                msg = self.make_msg(data, "Serie Regular")

            data = self.http(temporada=year, etapa="RR")
            if len(data) > 0:
                msg += "\n"
                msg += self.make_msg(data, "Serie Semifinal")

            data = self.http(temporada=year, etapa="SF")
            if len(data) > 0:
                msg += "\n"
                msg += self.make_msg(data, "Serie Final")

        except Exception as err:
            log.error("Pelota error: {}".format(err))
            msg = "❌ Error"

        self.adapter.bot.sendMessage(chat_id=message.chat_id, text=msg, parse_mode='Markdown', disable_web_page_preview = True)
