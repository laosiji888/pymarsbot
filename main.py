import atexit
import codecs
import io
import json
import logging
import threading
import time
from typing import Dict, Optional

import cv2
import numpy as np
import telethon
from telethon.events import NewMessage
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import (MessageMediaPhoto,
                               PeerChannel,
                               PeerUser,
                               Photo,
                               ChannelParticipantCreator,
                               ChannelParticipantAdmin, )
from config import admins, BOT_NAME, API_ID, API_HASH, BOT_SESSION_NAME, BOT_TOKEN

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)


def init_bot():
    bot_ = telethon.TelegramClient(
        BOT_SESSION_NAME,
        API_ID,
        API_HASH
    )
    bot_.start(bot_token=BOT_TOKEN)
    return bot_


bot = init_bot()


class MarsInfo:
    def __init__(self):
        self.unique_id_to_dhash: Dict[str, str] = dict()
        self.dhash_mars_count: Dict[str, int] = dict()
        self.dhash_last_msg: Dict[str, int] = dict()
        self.white_list_users: Dict[str, bool] = dict()

    def dhash_count_plus(self, dhash):
        self.dhash_mars_count[dhash] = self.dhash_mars_count.get(dhash, 0) + 1

    def add_uid_and_dhash(self, uid, dhash):
        self.unique_id_to_dhash[uid] = dhash
        self.dhash_count_plus(dhash)

    def has_uid(self, uid):
        return uid in self.unique_id_to_dhash.keys()

    def uid_count(self, uid):
        dhash = self.unique_id_to_dhash[uid]
        return self.dhash_count(dhash)

    def uid_count_plus(self, uid):
        dhash = self.unique_id_to_dhash[uid]
        self.dhash_count_plus(dhash)

    def dhash_count(self, dhash):
        return self.dhash_mars_count.get(dhash, 0)

    def get_uid_last_msg(self, uid):
        dhash = self.unique_id_to_dhash[uid]
        return self.get_dhash_last_msg(dhash)

    def get_dhash_last_msg(self, dhash):
        return self.dhash_last_msg[dhash]

    def set_uid_last_msg(self, uid, last_msg_id):
        dhash = self.unique_id_to_dhash[uid]
        self.set_dhash_last_msg(dhash, last_msg_id)

    def set_dhash_last_msg(self, dhash, last_msg_id):
        self.dhash_last_msg[dhash] = last_msg_id

    def add_white_list(self, user_id: int):
        user_id = str(user_id)
        self.white_list_users[user_id] = True

    def remove_white_list(self, user_id: int):
        user_id = str(user_id)
        self.white_list_users.pop(user_id)

    def user_in_white_list(self, user_id: int):
        user_id = str(user_id)
        return user_id in self.white_list_users

    def to_dict(self):
        data = {"uid2dhash": self.unique_id_to_dhash,
                "dhash_mar_count": self.dhash_mars_count,
                "dhash_last_msg": self.dhash_last_msg,
                "white_list_users": self.white_list_users}
        return data

    @staticmethod
    def from_dict(data):
        info = MarsInfo()
        info.dhash_mars_count = data["dhash_mar_count"]
        info.unique_id_to_dhash = data.get("uid2dhash", {})
        info.dhash_last_msg = data.get("dhash_last_msg", {})
        info.white_list_users = data.get("white_list_users", {})

        return info

    _use_mars_bot_groups = {}

    @classmethod
    def is_chat_enable(cls, chat_id):
        return chat_id in cls._use_mars_bot_groups.keys()

    @classmethod
    def get_chat_ins(cls, chat_id) -> Optional['MarsInfo']:
        return cls._use_mars_bot_groups.get(chat_id, None)

    @classmethod
    def add_chat(cls, chat_id):
        if cls.is_chat_enable(chat_id):
            return cls.get_chat_ins(chat_id)
        info = MarsInfo()
        cls._use_mars_bot_groups[chat_id] = info
        return info

    @classmethod
    def remove_chat(cls, chat_id):
        if cls.is_chat_enable(chat_id):
            cls._use_mars_bot_groups.pop(chat_id)

    @classmethod
    def save(cls, filename="mars.json"):
        with open(filename, "w", encoding="utf-8")as f:
            json.dump(cls._use_mars_bot_groups, f, default=lambda obj: obj.to_dict(), ensure_ascii=False,
                      sort_keys=True, indent=1)

    @classmethod
    def load(cls, filename="mars.json"):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, value in data.items():
                    key = int(key)
                    cls._use_mars_bot_groups[key] = cls.from_dict(value)
        except FileNotFoundError:
            return


def cmd_pattern(cmd):
    return r"/{cmd}(@{bot_name})?(\s+|$)".format(cmd=cmd, bot_name=BOT_NAME)


def get_bot_chat_id(peer) -> int:
    if isinstance(peer, PeerUser):
        return peer.user_id
    elif isinstance(peer, PeerChannel):
        to_id = -(1000000000000 + peer.channel_id)
        return to_id
    else:
        raise RuntimeError("peer 既不是用户也不是频道，无法推测发生了什么,to:{}".format(peer))


def get_raw_chat_id(peer) -> int:
    if isinstance(peer, PeerUser):
        return peer.user_id
    elif isinstance(peer, PeerChannel):
        return peer.channel_id
    else:
        raise RuntimeError("peer 既不是用户也不是频道，无法推测发生了什么,to:{}".format(peer))


def get_from_user(event: NewMessage.Event) -> int:
    peer = event.message.peer_id
    if isinstance(peer, PeerUser):
        return peer.user_id
    elif isinstance(peer, PeerChannel):
        peer = event.message.from_id
        return get_bot_chat_id(peer)
    raise RuntimeError("无法识别事件来源用户, event:{}".format(event))


def check_image(event: NewMessage.Event) -> bool:
    chat_id = get_bot_chat_id(event.message.peer_id)
    mars_info = MarsInfo.get_chat_ins(chat_id)
    user_id = get_from_user(event)
    if mars_info is not None and not mars_info.user_in_white_list(user_id):
        return isinstance(event.message.media, MessageMediaPhoto)


def dhash_bytes(data):
    data = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_ANYCOLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
    dhash_bits = np.greater(img[:, :8], img[:, 1:]).flatten()
    dhash = np.packbits(dhash_bits).tobytes()
    return codecs.encode(dhash, "hex").decode("ascii")


def generate_mars_text(link, count, threshold):
    msg_text_fmt = '你这张图片已经<a href="{0}">火星{1}次</a>了！'
    mars_x_times_fmt = '你已经让这张图片<a href="{0}">第{1}次火星</a>了，现在本车送你 ”火星之王“ 称号！'
    mars_grater_x_times_fmt = '火星之王，收了你的神通吧，这图都已经<a href="{0}">火星{1}次</a>了！'
    if count > threshold:
        return mars_grater_x_times_fmt.format(link, count)
    elif count == threshold:
        return mars_x_times_fmt.format(link, count)
    else:
        return msg_text_fmt.format(link, count)


@bot.on(NewMessage(func=check_image))
async def check_photo_mars(event: NewMessage.Event):
    chat_id = get_bot_chat_id(event.message.peer_id)
    photo: Photo = event.message.media.photo
    photo_uid = "uid" + str((photo.id * 10) + photo.dc_id)  # 该语句为唯一确定uid的方法
    mars_info = MarsInfo.get_chat_ins(chat_id)
    msg_id = event.message.id
    t_me_link_fmt = "https://t.me/c/{}/{}"

    if mars_info.has_uid(photo_uid):
        count = mars_info.uid_count(photo_uid)
        mars_info.uid_count_plus(photo_uid)
        last_msg_id = mars_info.get_uid_last_msg(photo_uid)
        link = t_me_link_fmt.format(get_raw_chat_id(event.message.peer_id), last_msg_id)
        msg_text = generate_mars_text(link, count, 10)
        mars_info.set_uid_last_msg(photo_uid, msg_id)
    else:
        buffer = io.BytesIO()
        await bot.download_media(event.message, buffer, thumb=-1)
        buffer.seek(0)
        data = buffer.read()
        dhash = dhash_bytes(data)
        count = mars_info.dhash_count(dhash)
        mars_info.add_uid_and_dhash(photo_uid, dhash)
        if count > 0:
            last_msg_id = mars_info.get_dhash_last_msg(dhash)
            link = t_me_link_fmt.format(get_raw_chat_id(event.message.peer_id), last_msg_id)
            msg_text = generate_mars_text(link, count, 10)
            mars_info.set_dhash_last_msg(dhash, msg_id)
        else:
            mars_info.set_dhash_last_msg(dhash, msg_id)
            return
    await bot.send_message(event.chat_id, msg_text, reply_to=event.message.id, parse_mode="HTML")


@bot.on(NewMessage(pattern=cmd_pattern("enable")))
async def chat_enable(event: NewMessage.Event):
    if not isinstance(event.message.peer_id, PeerChannel):
        await bot.send_message(event.chat_id, "该对话并非 群组/频道 ，无法正常配置，如果你认为该情况不应该出现，请联系开发者。")
        return
    participant = await bot(GetParticipantRequest(event.message.peer_id, event.message.from_id))
    if not isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
        await bot.send_message(event.chat_id, "只有该群的 创建者/管理员 可以改变火星车状态")
        return
    chat_id = get_bot_chat_id(event.message.peer_id)
    if MarsInfo.is_chat_enable(chat_id):
        await bot.send_message(event.chat_id, "这个群组已经启用了。", reply_to=event.message.id)
    else:
        MarsInfo.add_chat(chat_id)
        await bot.send_message(event.chat_id, "启用火星车。", reply_to=event.message.id)


@bot.on(NewMessage(pattern=cmd_pattern("disable")))
async def chat_disable(event: NewMessage.Event):
    if not isinstance(event.message.peer_id, PeerChannel):
        await bot.send_message(event.chat_id, "该对话并非 群组/频道 ，无法正常配置，如果你认为该情况不应该出现，请联系开发者。")
        return
    participant = await bot(GetParticipantRequest(event.message.peer_id, event.message.from_id))
    if not isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
        await bot.send_message(event.chat_id, "只有该群的 创建者/管理员 可以改变火星车状态")
        return
    chat_id = get_bot_chat_id(event.message.peer_id)
    if MarsInfo.is_chat_enable(chat_id):
        MarsInfo.remove_chat(chat_id)
        await bot.send_message(event.chat_id, "已停用，存储的相关 图片dhash、图片ID、消息ID等将会被移除。", reply_to=event.message.id)
    else:
        await bot.send_message(event.chat_id, "这个群组根本就没启用过。")


@bot.on(NewMessage(pattern=cmd_pattern("add_whitelist")))
async def add_white_list(event: NewMessage.Event):
    chat_id = get_bot_chat_id(event.message.peer_id)
    mars_info = MarsInfo.get_chat_ins(chat_id)
    if mars_info is None:
        await bot.send_message(event.chat_id, "该群组/频道没有启用火星车，无法添加用户白名单", reply_to=event.message.id)
        return
    user_id = get_from_user(event)
    if mars_info.user_in_white_list(user_id):
        await bot.send_message(event.chat_id,
                               "用户 `uid:{}` 已经在火星车白名单里了".format(user_id)
                               , reply_to=event.message.id, parse_mode="markdown")
    else:
        mars_info.add_white_list(user_id)
        await bot.send_message(event.chat_id,
                               "用户 `uid:{}` 已加入火星车白名单".format(user_id)
                               , reply_to=event.message.id, parse_mode="markdown")


@bot.on(NewMessage(pattern=cmd_pattern("remove_whitelist")))
async def remove_white_list(event: NewMessage.Event):
    chat_id = get_bot_chat_id(event.message.peer_id)
    mars_info = MarsInfo.get_chat_ins(chat_id)
    if mars_info is None:
        await bot.send_message(event.chat_id, "该群组/频道没有启用火星车，无法添加用户白名单", reply_to=event.message.id)
        return
    user_id = get_from_user(event)
    if mars_info.user_in_white_list(user_id):
        mars_info.remove_white_list(user_id)
        await bot.send_message(event.chat_id,
                               "用户 `uid:{}` 已从白名单中移除".format(user_id)
                               , reply_to=event.message.id, parse_mode="markdown")
    else:
        await bot.send_message(event.chat_id,
                               "用户 `uid:{}` 并没有在火星车白名单里".format(user_id)
                               , reply_to=event.message.id, parse_mode="markdown")


@bot.on(NewMessage(chats=admins, pattern=r"^/save"))
async def save(event: NewMessage.Event):
    MarsInfo.save()
    await bot.send_message(event.chat_id, "manual saved")


@bot.on(NewMessage(from_users=admins, pattern=r"/msinfo"))
async def get_msg_info(event: NewMessage.Event):
    print(event.message.stringify())
    reply_message = await event.message.get_reply_message()
    print(reply_message.stringify())


def timer_save_threading():
    """
    每过12小时保存
    :return:
    """
    while True:
        time.sleep(86400 / 2)
        MarsInfo.save()


def test_dhash(filename):
    """
    测试用函数
    :param filename:
    :return:
    """
    with open(filename, "rb") as f:
        return dhash_bytes(f.read())


if __name__ == '__main__':
    MarsInfo.load()
    atexit.register(MarsInfo.save)
    t = threading.Thread(target=timer_save_threading, daemon=True)
    t.start()
    with bot:
        bot.run_until_disconnected()
