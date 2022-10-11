API_ID: int = 18394898
API_HASH: str = "655948dbb9ee926796a73bd100e43b2a"
BOT_TOKEN: str = "5789474082:AAHCHXXNkA39W_56JhcVsllzI1GWxcqKu40"
BOT_SESSION_NAME: str = "huaji"  # 任何合法的文件名都可以
BOT_NAME: str = "@huoxingche_bot"  # 申请的bot 的username， @开头的那个，这里面的 @ 不能删
admins = []  # 能操作bot的userID，实际上就是能手动保存

CAN_RUN = False
if not CAN_RUN:
    # 如果你觉得配置好了把这里删了就行了，或者把 CAN_RUN 改为True
    print("该bot基于Telethon+OpenCV开发\n"
          "部署需要手动申请 API_HASH API_ID BOT_TOKEN\n"
          "其中的大部分特性需要Python3.7及以上版本")
    exit(1)
