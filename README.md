# ChaT
![image](https://github.com/CTDancer/ChaT/assets/89793506/d9686642-a9cf-46f1-8344-ebed417d8274)

# 功能介绍
这是一个基于数据库的社交网络平台。用户可以在各个分区中发帖交流，每个帖子都有相应的回复区。用户可以点赞、收藏、编辑、删除帖子和回复（回复无法收藏）

一共有三种不同权限的用户：
1. 普通用户
2. 普通管理员：可以删除所有帖子
3. 超级管理员：不仅可以删除所有帖子，还可以将普通管理员降职为普通用户，将普通用户升职为普通管理员

（超级管理员的用户名和密码都为admin）

# 前后端介绍
后端框架：Django
前端框架：Vue，使用组件库 Ant design vue pro

### 运行方式
先配置环境
```
conda create -n dbpj python=3.9
conda activate dbpj
pip install -r requirements.txt
```
再启动后端：
```
cd backend
python manage.py runserver
```

最后启动前端：

先新建一个cmd终端

在第一次运行时要先安装ant design库
```
cd frontend
yarn install
```
之后只需用如下命令即可启动前端：
```
conda activate dbpj
cd frontend
set NODE_OPTIONS=--openssl-legacy-provider
yarn run serve
```
