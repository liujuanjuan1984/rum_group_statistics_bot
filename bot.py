"""
统计 group 的基本概况，并发布到 group。
通过 fullnode 遍历 block 来统计。
"""

import datetime
import json
import logging
import os

from quorum_data_py import feed
from quorum_fullnode_py import FullNode

logger = logging.getLogger(__name__)
__version__ = "0.1.0"
logger.info("Version %s", __version__)


def timestamp_to_beijing_day(timestamp):
    """timestamp 转换为 北京地区的 日期，格式为 %Y-%m-%d，比如：2021-04-13"""
    timestamp = int(str(timestamp)[:10])
    utc_time = datetime.datetime.utcfromtimestamp(timestamp)
    beijing_offset = datetime.timedelta(hours=8)
    beijing_time = utc_time + beijing_offset
    return beijing_time.strftime("%Y-%m-%d")


class GroupStatisticsBot:
    """group statistics bot"""

    def __init__(self, client: FullNode, group_id: str, data_file: str):
        self.rum = client
        self.rum.group_id = group_id
        self.group_name = self.rum.api.group_info()["group_name"]
        self.data_file = data_file

        if not os.path.exists(data_file):
            self.data = {
                "block": {},
                "trx": {},
                "user": {},
                "process": 0,  # 已经完成的 block 高度
                "to_group": {},
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1)
        else:
            with open(data_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def update_status(self):
        """update status data"""
        info = self.rum.api.group_info()
        height = info["currt_top_block"]

        start_height = self.data["process"] + 1
        for i in range(start_height, height + 1):
            iblock = self.rum.api.get_block(i)
            day = timestamp_to_beijing_day(iblock["TimeStamp"])
            if day not in self.data["block"]:
                self.data["block"][day] = 1
            else:
                self.data["block"][day] += 1

            for itrx in iblock["Trxs"]:
                day = timestamp_to_beijing_day(itrx["TimeStamp"])
                if day not in self.data["trx"]:
                    self.data["trx"][day] = 1
                else:
                    self.data["trx"][day] += 1
                if day not in self.data["user"]:
                    self.data["user"][day] = [itrx["SenderPubkey"]]
                elif itrx["SenderPubkey"] not in self.data["user"][day]:
                    self.data["user"][day].append(itrx["SenderPubkey"])
            self.data["process"] = i

    def post_status(self, day: str = None):
        """post status to group, default is yesterday's status, day: %Y-%m-%d"""
        day = day or datetime.datetime.now() + datetime.timedelta(days=-1).strftime(
            "%Y-%m-%d"
        )
        logger.info("try to post status to group %s at %s", self.group_name, day)
        self.update_status()
        if day not in self.data["to_group"] and day in self.data["block"]:
            content = f"当前区块高度 {self.data['process']}，已连接 {len(self.rum.api.group_network() or [])} 个节点。{day} 概况：新增 {self.data['block'][day]} 个区块、{self.data['trx'][day]} 条 Trxs，当天活跃 {len(self.data['user'][day])} 个账号。"
            resp = self.rum.api.post_content(feed.new_post(content))
            if "trx_id" in resp:
                self.data["to_group"][day] = resp["trx_id"]
                logger.info(
                    "post status to group %s at %s success", self.group_name, day
                )
                with open(self.data_file, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=1)
