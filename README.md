### zk_monitor.py
zk论坛关键字监控，实时邮箱提醒

### 邮箱配置
发送者邮箱账号开启客户端授权码，更安全！！   
接受者邮箱账号添加发送者进白名单，重要！！

### 脚本配置
```
# 监控关键字
KEYWORD = {
    'include': '密令|红包|水|速度|神券|京豆',
    'exclude': '权限|水贴'
}
# 发送者
SENDER = {
    'name': '小分队',
    'email': 'youremail@126.com',
    'smtp': 'smtp.126.com',
    'pass': 'yourpass'
}
# 接受者
RECEIVERS = [
    {
        'name': 'username',
        'email': 'youremail@qq.com',
    }
]
```

### 脚本使用
Windows平台：使用前提pip install pyquery，可以配合系统计划任务执行脚本，要求Python3.5   
无服务云函数：免费运行资源，打包zip部署至云环境，打包步骤请看[这里](https://cloud.tencent.com/document/product/583/9702)，要求Python3.6