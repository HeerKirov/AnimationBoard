# Animation Board
> Coding...

## 部署
### 配置文件
```bash
cp config.py.example config.py
```
执行此命令，从配置文件模版复制一份文件，并酌情修改。
```python
URL_PREFIX = 'animation-board/'     # 在URL中添加在后续地址前的前缀

DEBUG = True                        # debug模式
SECRET_KEY = ''                     # 密钥

DATABASE = {                        # postgreSQL数据库的配置
    'DATABASE': 'animation_board',  # 数据库的名称
    'USERNAME': 'postgres',         # 数据库用户名
    'PASSWORD': '',                 # 密码
    'HOST': 'localhost',            # 连接的主机HOST
    'PORT': '5432'                  # 连接的端口PORT
}

INITIAL_ADMIN_USER = {              # 初始化数据库时，会使用这些信息创建第一个超级管理员
    'username': 'admin',            # 管理员的用户名
    'password': 'admin',            # 管理员的密码
    'name': 'Administrator'         # 管理员的昵称
}

INITIAL_SETTING = {                 # 初始化数据库时，会使用这些信息初始化全局设置
    'register_mode': 'OPEN'         # 注册限制，有3个可选项：'OPEN'=开放注册, 'ONLY_CODE'=只允许注册码, 'CLOSE'=关闭注册
}

AUTO_UPDATE_SETTINGS = {            # 番剧自动刷新服务的crontab配置
    'enable': True,                 # 启用自动刷新服务
    'interval': '*/15 * * * *'      # 触发时间配置
}

COVER_STORAGE = {                   # 封面上传服务的配置
    'FILEPATH': 'cover'             # 封面文件存储在static文件夹中的位置
}

```
### 安装依赖
在开始安装之前，首先确保安装了`python 3.5`及以上的版本，`pip3`，`postgreSQL 9.6`及以上的版本。  
```bash
pip3 install -r requirements.txt
python3 manage.py migrate
```
### 测试
```bash
python3 manage.py runserver 0.0.0.0:8000    # 启动测试服务器
```
后端使用crontab来做定时任务。因此定时任务只能在Unix系统上使用。
```bash
python3 manage.py crontab add       # 注册，启动定时任务
python3 manage.py crontab remove    # 移除定时任务
```