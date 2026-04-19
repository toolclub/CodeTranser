# ============================================================
# chatflow-sandbox(从 ChatFlow 沙箱镜像复制,**镜像名保持一致**)
#
# 与 ChatFlow 项目共享同一个镜像 tag(`chatflow-sandbox:latest`):
#   - 本地有就直接复用,不重新 build
#   - 本地没就从这份 Dockerfile build,跟 ChatFlow build 出来的等价
#
# Cascade 通过 docker-compose 起容器实例,容器名独立(cascade-sandbox),
# 镜像层不冲突,可以和 ChatFlow 的 chatflow-sandbox 容器并存运行。
# ============================================================
FROM fullstack-dev:latest

ENV DEBIAN_FRONTEND=noninteractive

# 只装 SSH 服务(Python/Node/Java/C++ 工具链已在 base 中)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    tree \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 沙箱工作根目录
RUN mkdir -p /sandbox && chmod 777 /sandbox

# SSH 配置
RUN mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# root 密码(内网/dev;生产 K8S 改 SSH key)
ARG SANDBOX_ROOT_PASSWORD=sandbox123
RUN echo "root:${SANDBOX_ROOT_PASSWORD}" | chpasswd

EXPOSE 22

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD nc -z localhost 22 || exit 1

CMD ["/usr/sbin/sshd", "-D"]
