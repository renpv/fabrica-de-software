# Imagem do ambiente do Cursor (agentes na nuvem) para este repositório.
# Não copia o projeto: o Cursor faz o checkout do commit certo.
# Segue o roteiro da doc do Cursor para Docker dentro do agente
# (https://cursor.com/docs/cloud-agent/setup): Docker CE + compose,
# fuse-overlayfs, iptables legado e usuário ubuntu com sudo sem senha.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg git jq sudo build-essential \
      fuse-overlayfs iptables \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" \
       > /etc/apt/sources.list.d/docker.list \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli.gpg] https://cli.github.com/packages stable main" \
       > /etc/apt/sources.list.d/github-cli.list \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends \
      docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
      gh nodejs \
    && rm -rf /var/lib/apt/lists/*

# Docker dentro do agente: overlay em FUSE e iptables legado.
RUN mkdir -p /etc/docker \
    && echo '{"storage-driver": "fuse-overlayfs"}' > /etc/docker/daemon.json \
    && update-alternatives --set iptables /usr/sbin/iptables-legacy \
    && update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# A imagem do Ubuntu 24.04 já traz o usuário ubuntu.
RUN usermod -aG docker,sudo ubuntu \
    && echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

USER ubuntu
ENV PATH="/home/ubuntu/.local/bin:${PATH}"
# uv e Python 3.13 (versão fixada em backend/.python-version).
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /home/ubuntu/.local/bin/uv python install 3.13
