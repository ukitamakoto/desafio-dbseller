#!/usr/bin/env bash
# Sobe o OrangeHRM 5.9 isolado em http://localhost:8200, instala e deixa pronto para a suíte.
set -euo pipefail
cd "$(dirname "$0")"
docker compose up -d --wait
docker compose cp cli_install_config.yaml orangehrm:/var/www/html/installer/cli_install_config.yaml
docker compose exec -T orangehrm php installer/cli_install.php
curl -fsS -o /dev/null http://localhost:8200/web/index.php/auth/login && echo "OrangeHRM isolado pronto em http://localhost:8200"
