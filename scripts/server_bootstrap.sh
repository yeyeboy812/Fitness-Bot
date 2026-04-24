#!/usr/bin/env bash
# One-shot server setup for Ubuntu 22.04/24.04.
# Installs Docker, Docker Compose plugin, git, firewall rules, and a deploy user.
# Run as root: curl -fsSL ... | bash  OR  bash scripts/server_bootstrap.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo bash $0)"
  exit 1
fi

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/fitness-bot}"

echo "==> apt update & base packages"
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg git ufw

echo "==> Docker install (official repo)"
install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

echo "==> Deploy user: $DEPLOY_USER"
if ! id "$DEPLOY_USER" &>/dev/null; then
  adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

echo "==> App dir: $APP_DIR"
mkdir -p "$APP_DIR"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

echo "==> SSH key for $DEPLOY_USER"
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
if [[ -f /root/.ssh/authorized_keys ]]; then
  cp /root/.ssh/authorized_keys "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
  chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"
  echo "   copied root's authorized_keys"
fi

echo "==> UFW firewall (22/tcp only)"
ufw allow OpenSSH
ufw --force enable

echo "==> Done."
echo "Next steps:"
echo "  1. ssh $DEPLOY_USER@<server-ip>"
echo "  2. cd $APP_DIR"
echo "  3. git clone <repo-url> ."
echo "  4. cp .env.prod.example .env && \$EDITOR .env"
echo "  5. bash scripts/deploy.sh"
