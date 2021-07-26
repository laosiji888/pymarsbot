# Telegram火星bot  
去年闲来无事写的火星车bot，可以检测群/频道里已经发过的图。   
在同一个群里，如果在一张图被别人发过，那么再次发送这张图时这个bot则会提示火星。  
这个功能基于Telegram的唯一ID+使用OpenCV对图片进行 `DHASH`  
大致流程：  
当检测到接收的图片唯一ID重复时，不会下载图片，直接在缓存中寻找唯一ID对应的DHASH。
而当缓存中不存在该唯一ID，则下载图片，进行DHASH，查找该DHASH对应的图片在这个群里被发送的次数。  
特点：
- 不会保存图片，所有的操作均在内存中完成。  
- 不会检测文件形式的图片，不会检测视频/Gif/Stickers 。  

## 部署
1. clone本库，配置 `config.py`中的`API_ID`, `API_HASH` ,`BOT_TOKEN`等变量。
2. 安装依赖。  `pip3 install requirements.txt`
3. 执行 `python3 marsbot.py`即可

理论上该项目通用于 Windows/Mac/Linux 平台，已在Windows(AMD64)和Linux(Ubuntu 18.04/KVM/AMD64)平台上测试成功。
