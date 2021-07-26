API_ID: int = 0
API_HASH: str = "get API_ID and API_HASH from telegram link:https://core.telegram.org/api/obtaining_api_id"
BOT_TOKEN: str = "get from bot father"
BOT_SESSION_NAME: str = "any valid file name"  # 任何合法的文件名都可以
BOT_NAME: str = "@username_bot"  # 申请的bot 的username， @开头的那个，这里面的 @ 不能删
admins = []  # 能操作bot的userID，实际上就是能手动保存

CAN_RUN = False
if not CAN_RUN:
    # 如果你觉得配置好了把这里删了就行了，或者把 CAN_RUN 改为True
    print("该bot基于Telethon+OpenCV开发\n"
          "部署需要手动申请 API_HASH API_ID BOT_TOKEN\n"
          "其中的大部分特性需要Python3.7及以上版本")
    exit(1)
