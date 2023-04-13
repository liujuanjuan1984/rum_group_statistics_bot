import logging

from quorum_fullnode_py import FullNode

from bot import GroupStatisticsBot

logging.basicConfig(level=logging.INFO)

rum = FullNode(port=11002)
group_id = "bb574631-f043-4690-a3d0-c2d85e9914a3"
data_file = f"group_{group_id}_status.json"

bot = GroupStatisticsBot(rum, group_id, data_file)
bot.post_status("2023-04-12")
