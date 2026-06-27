# 云服务器部署

推荐使用云服务器 Docker 部署。别人访问网站时只消耗云服务器资源，不会占用你的电脑性能，也不要求你的电脑一直开机。

## 为什么选云服务器

- 云服务器：适合公开访问，稳定，和本机解耦。
- 内网穿透：依赖你电脑持续开机，访问量会消耗本机和本地网络。
- 路由器端口映射：暴露家庭网络，维护成本和安全风险更高。
- VPN：适合私人访问，不适合公开用户直接打开网页。

## 最低建议配置

- 1 核 1GB 可运行；建议 1 核 2GB 更稳。
- Ubuntu 22.04/24.04。
- 开放安全组端口：`80`、`443`。如临时直连调试，再开放 `8000`。

## 首次部署

在云服务器执行：

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

拉取你的 GitHub 仓库：

```bash
git clone <你的GitHub仓库地址> Tao
cd Tao
cp deploy/cloud/.env.example deploy/cloud/.env
```

如果暂时没有域名，保持：

```text
ACCORDANCE_SITE_ADDRESS=:80
```

如果有域名，把 `deploy/cloud/.env` 改成：

```text
ACCORDANCE_SITE_ADDRESS=你的域名
```

启动：

```bash
docker compose --env-file deploy/cloud/.env -f deploy/cloud/docker-compose.yml up -d --build
```

查看状态：

```bash
docker compose --env-file deploy/cloud/.env -f deploy/cloud/docker-compose.yml ps
docker compose --env-file deploy/cloud/.env -f deploy/cloud/docker-compose.yml logs -f --tail=100
```

看到 `accordance-web` 为 `healthy`，`caddy` 为运行中后，再继续访问测试。

访问：

```text
http://服务器公网IP
```

有域名时访问：

```text
https://你的域名
```

上线验收：

```bash
curl -I http://服务器公网IP/health
curl -I http://服务器公网IP/
```

如果配置了域名，把上面的地址替换为 `https://你的域名`。正常情况下 `/health` 返回 `200`，首页响应头应包含 `Cache-Control: no-store`、`X-Robots-Tag: noindex, nofollow`。

## 更新部署

你本机修改后推送 GitHub，然后在云服务器执行：

```bash
cd Tao
git pull
docker compose --env-file deploy/cloud/.env -f deploy/cloud/docker-compose.yml up -d --build
```

## 隐私与数据

- 匿名用户历史存放在 Docker volume `accordance_web_data`，不会进入 GitHub。
- 不需要注册登录；每台设备按匿名 `client_id` 隔离历史。
- 不提供查看其他用户历史的入口。
- Caddy 默认未开启访问日志；应用日志也不记录用户问题正文。
- `deploy/cloud/.env` 属于服务器本地配置，已加入 Git 忽略，不应上传到公开仓库。
- 清空单台设备历史应优先在网页“近期记录”中操作。
- 全量清空云端匿名历史会删除所有访问者记录；执行前应先备份并确认影响范围。
