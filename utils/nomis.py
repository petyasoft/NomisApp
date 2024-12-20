from urllib.parse import parse_qs,unquote
from utils.core import logger
from fake_useragent import UserAgent
from pyrogram import Client
from data import config
from datetime import datetime, timezone

from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName
import requests
import aiohttp
import asyncio
import random
import json
import time


class Nomis:
    def __init__(self, thread: int, account: str, proxy : str):
        self.thread = thread
        self.name = account
        if proxy:
            proxy_client = {
                "scheme": config.PROXY_TYPE,
                "hostname": proxy.split(':')[0],
                "port": int(proxy.split(':')[1]),
                "username": proxy.split(':')[2],
                "password": proxy.split(':')[3],
            }
            self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR, proxy=proxy_client)
        else:
            self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR)
                
        if proxy:
            self.proxy = f"{config.PROXY_TYPE}://{proxy.split(':')[2]}:{proxy.split(':')[3]}@{proxy.split(':')[0]}:{proxy.split(':')[1]}"
        else:
            self.proxy = None
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://telegram.nomis.cc',
            'priority': 'u=1, i',
            'referer': 'https://telegram.nomis.cc/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': UserAgent().random,
        }
        self.session = aiohttp.ClientSession(headers=headers, trust_env=True, connector=aiohttp.TCPConnector(verify_ssl=False))

    async def main(self):
        await asyncio.sleep(random.uniform(*config.ACC_DELAY))
        while True:
            try:
                tg_webdata = await self.get_tg_web_data()
                if not tg_webdata:
                    await self.session.close()
                    return 0
                user_info = await self.auth()
                if user_info == False:
                    await self.session.close()
                    return 0
                logger.info(f"NOMIS | main | Thread {self.thread} | {self.name} | Start! | PROXY : {self.proxy}")
            except Exception as err:
                logger.error(f"NOMIS | main | Thread {self.thread} | {self.name} | {err}")
                await self.session.close()
                return 0
            try:
                farm_data = await self.farm_data()
                if farm_data['nextFarmClaimAt'] == None:
                    await self.start_farm()
                else:
                    ts_now = datetime.now(tz=timezone.utc).timestamp()*1000
                    farm_end = self.convert_to_timestamp(date_str=farm_data['nextFarmClaimAt'])
                    if farm_end <= ts_now:
                        await self.claim_farm()
                        await asyncio.sleep(random.uniform(*config.START_SLEEP))
                        await self.start_farm()
                
                tasks_list = await self.get_tasks()
                await asyncio.sleep(random.uniform(*config.MINI_SLEEP))
                for tasks in tasks_list:
                    tasks = tasks['ton_twa_tasks']
                    for task in tasks:
                        if task['id'] in [146,145,144,147,196,171,17,201,198,199,200,95,40,167,125,103,115,5,103,61,23,140,141,206,200]:
                            continue
                        if random.randint(0,1) == 0:
                            await self.verify_task(task_id=task['id'])
                            await asyncio.sleep(random.uniform(*config.TASKS_SLEEP))
                            
                logger.info(f"NOMIS | main | Thread {self.thread} | {self.name} | Круг окончен")
                await asyncio.sleep(random.uniform(*config.END_SLEEP))
            except Exception as err:
                logger.error(f"NOMIS | main | Thread {self.thread} | {self.name} | {err}")
                await asyncio.sleep(5*random.randint(*config.MINI_SLEEP))

    async def get_tasks(self):
        resp = await self.session.get("https://cms-api.nomis.cc/api/users/tasks",proxy = self.proxy)
        return await resp.json()

    async def verify_task(self,task_id : int):
        try:
            json_data = {
                'task_id': task_id,
            }

            response = await self.session.post('https://cms-api.nomis.cc/api/users/claim-task',json=json_data,proxy = self.proxy)
            if (await response.json())['data']['result']:
                logger.success(f"NOMIS | verify_task | Thread {self.thread} | {self.name} | Claimed {(await response.json())['data']['reward']/1000}")
            return await response.json()
        except:
            pass

    
    async def farm_data(self):
        response = await self.session.get('https://cms-api.nomis.cc/api/users/farm-data',proxy=self.proxy)
        return await response.json()
       

    async def claim_farm(self):
        json_data = {}
        response = await self.session.post("https://cms-api.nomis.cc/api/users/claim-farm",json=json_data, proxy = self.proxy)
        logger.success(f"NOMIS | claim_farm | Thread {self.thread} | {self.name} | Claimed farm ")
        return await response.json()

    async def start_farm(self):
        json_data = {}
        response = await self.session.post("https://cms-api.nomis.cc/api/users/start-farm",json=json_data,headers=self.session.headers, proxy = self.proxy)
        logger.success(f"NOMIS | start_farm | Thread {self.thread} | {self.name} | Start Farm")
        return await response.json()
    
    async def auth(self):
        json_data = {
            'telegram_user_id': self.telegram_user_id,
            'telegram_username': self.telegram_username,
            'referrer': self.referrer[4:],
        }
        response = await self.session.post('https://cms-api.nomis.cc/api/users/auth',json=json_data,proxy=self.proxy)
        self.user_id = (await response.json())['id']
        return await response.json()

    async def get_tg_web_data(self):
        async with self.client:
            try:
                bot = await self.client.resolve_peer('NomisAppBot')
                app = InputBotAppShortName(bot_id=bot, short_name="app")


                web_view = await self.client.invoke(RequestAppWebView(
                        peer=bot,
                        app=app,
                        platform='android',
                        write_allowed=True,
                        start_param=config.REFERRAL_CODE,
                    ))

                auth_url = web_view.url
                authData = unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
                self.telegram_user_id = str((json.loads(parse_qs(unquote(authData))['user'][0])['id']))
                self.telegram_username = (json.loads(parse_qs(unquote(authData))['user'][0])['username'])
                self.referrer = parse_qs(unquote(authData))['start_param'][0]
                self.session.headers['x-app-init-data'] = (unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]))
                return True
            except Exception as err:
                logger.error(f"NOMIS | get_tg_webdata | Thread {self.thread} | {self.name} | {err}")
                if 'USER_DEACTIVATED_BAN' in str(err):
                    logger.error(f"NOMIS | get_tg_webdata | Thread {self.thread} | {self.name} | USER BANNED")
                return False

    def convert_to_timestamp(self,date_str):
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = int(time.mktime(dt.timetuple()) * 1000 + config.UTC*60*1000)
        return timestamp
