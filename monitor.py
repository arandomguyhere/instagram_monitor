import os
import json
import pytz
import requests

from lxml import html
from requests import Response
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


class TimeConverter:
    @staticmethod
    def convert_unix_timestamp(timestamp: int) -> tuple[str, str]:
        dt_server = datetime.fromtimestamp(timestamp, tz=pytz.timezone('UTC'))
        dt_server -= timedelta(days=1)
        dt_local = dt_server.astimezone(pytz.timezone('Asia/Kolkata'))

        formatted_time = dt_local.strftime("%d %B %Y %I:%M %p %A")
        formatted_date = dt_local.strftime("%Y-%m-%d")

        return formatted_time, formatted_date


class InstaPost:
    def __init__(self, media_id: Optional[str] = ''):
        self._reel_id = None
        self.reel_id = media_id
        self.cookies = {}

        self.username = 'demos'
        self.items = {}
        self.media_list = []

        self.session = requests.Session()
        self.folder_path = '.'

    @property
    def reel_id(self):
        return self._reel_id

    @reel_id.setter
    def reel_id(self, media_id):
        self._reel_id = self.get_media_slug(media_id)

    def get_media_slug(self, media_id: str) -> str:
        return media_id.split('?')[0].strip('/').split('/')[-1].strip()

    def print(self, check: Optional[bool] = False) -> None:
        if check:
            print(f'Post downloaded successfully at {self.folder_path}/post/{self.username}')
        else:
            print("Post not found or try again....")

    def media_download(self) -> Dict:
        if not self.validate_inputs():
            print("post id is missing !!!")
            return {}

        response = self.make_initial_request()
        if not response:
            self.print()
            return {}

        json_data = self.make_second_request(response)
        if not json_data:
            self.print()
            return {}

        media_data = self.get_media(json_data)

        if not media_data['Media Data']:
            self.print()
            return {}

        with open(f'{self.folder_path}/post/{self.username}/{self.reel_id}.json', 'w') as f:
            json.dump({self.username: media_data}, f)

        with open(f'{self.folder_path}/post/{self.username}/{self.reel_id}-main.json', 'w') as f:
            json.dump(self.items, f)

        self.print(True)
        return {self.username: media_data}

    def validate_inputs(self) -> bool:
        return bool(self.reel_id)

    def make_initial_request(self) -> Response | bool:
        try:
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
            }

            response = self.session.get(f'https://www.instagram.com/p/{self.reel_id}/', headers=headers)
            try:
                con = html.fromstring(response.text)
                pk = con.xpath('//meta[@property="instapp:owner_user_id"]/@content')[0]
            except:
                pk = ''

            return response if pk else None

        except:
            return None

    def make_second_request(self, response) -> Dict:
        try:
            con = html.fromstring(response.text)
            try:
                self.username = f"""{con.xpath('//meta[@name="twitter:title"]/@content')[0]}""".split(')')[0].split('@')[1]
            except:
                pass

            headers, data = self.set_parameters(response)

            session = requests.Session()
            session.cookies.update(self.cookies)

            response = session.post('https://www.instagram.com/graphql/query', cookies=self.cookies, headers=headers, data=data)

            try:
                self.items = response.json()['data']['xdt_shortcode_media']
            except:
                pass
            try:
                self.media_list = [nodes['node'] for nodes in self.items['edge_sidecar_to_children']['edges']]
            except:
                self.media_list = [self.items] if self.items else []

            return response.json() if self.media_list else {}

        except:
            return {}

    def set_parameters(self, response) -> Tuple[Dict, Dict]:
        # Basic parameter extractors (simplified version here)
        csrf_token = response.text.split('csrf_token":"')[1].split('"')[0] if 'csrf_token":"' in response.text else ''

        self.cookies = {
            'csrftoken': csrf_token
        }

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'x-csrftoken': csrf_token,
            'content-type': 'application/x-www-form-urlencoded'
        }

        data = {
            'variables': json.dumps({"shortcode": self.reel_id}),
            'doc_id': '8845758582119845'
        }

        return headers, data

    def get_media(self, json_data) -> Dict:
        try:
            items = self.items

            try:
                self.username = json_data['data']['xdt_shortcode_media']['owner']['username']
            except:
                pass

            description = self.get_media_description()
            post_time, _ = TimeConverter.convert_unix_timestamp(int(items['taken_at_timestamp']))

            processed_items = self.process_media_items()

            return {
                'url': f"https://www.instagram.com/p/{items['shortcode']}/",
                'description': description,
                'Time': post_time,
                'Media Data': processed_items
            }

        except:
            return {'Media Data': []}

    def process_media_items(self) -> List:
        try:
            processed_items = []

            for item in self.media_list:
                is_video = item['is_video']
                try:
                    video_links = item['video_url'] if is_video else item['display_url']
                except:
                    video_links = ''

                if not video_links:
                    continue

                media_item = {
                    'Link': video_links
                }

                processed_items.append(media_item)

            return processed_items

        except:
            return []

    def get_media_description(self) -> str:
        try:
            des = self.items['edge_media_to_caption']['edges'][0]['node']['text']
            return des if des else ''
        except:
            return ''
