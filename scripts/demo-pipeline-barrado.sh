#!/usr/bin/env bash
# Evidência obrigatória: "mostrar uma execução barrada e a corrigida".
#
#   ./scripts/demo-pipeline-barrado.sh segredo          -> Gitleaks barra uma chave no código
#   ./scripts/demo-pipeline-barrado.sh vulnerabilidade  -> Trivy barra uma dependência com CVE alta
#   ./scripts/demo-pipeline-barrado.sh corrigir         -> corrige a demo da branch atual
#
# Tudo acontece numa branch demo/*: a main e a produção não são tocadas.
# A chave é gerada na hora e é falsa; nada com cara de segredo fica neste script.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -z "$(git status --porcelain)" ]] || { echo "Faça commit ou stash das mudanças antes." >&2; exit 1; }

case "${1:-}" in
  segredo)
    git switch -c demo/segredo-vazado
    chave=$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 40)
    printf '# Arquivo da demonstração do Gitleaks\nSP156_API_KEY = "%s"\n' "$chave" > api/app/config_demo.py
    git add api/app/config_demo.py
    git commit -m "demo: chave de API esquecida no código"
    git push -u origin demo/segredo-vazado
    echo "Veja o Actions: o job 'Segredos (Gitleaks)' deve falhar. Print do log e do grafo."
    ;;
  vulnerabilidade)
    git switch -c demo/dependencia-vulneravel
    echo "urllib3==1.26.4" >> api/requirements.txt
    git commit -am "demo: dependência com CVE conhecida"
    git push -u origin demo/dependencia-vulneravel
    echo "Veja o Actions: o passo 'Trivy — vulnerabilidades da imagem' deve falhar."
    ;;
  corrigir)
    branch=$(git branch --show-current)
    case "$branch" in
      demo/segredo-vazado)
        # Apagar num commit novo NÃO basta: o segredo continua no histórico (e o
        # Gitleaks continua barrando). O certo é reescrever o histórico e, num
        # caso real, revogar a chave na hora.
        git reset --hard HEAD~1
        printf 'import os\n\n# Correção: a chave vem do ambiente (Container App secret), nunca do código.\nSP156_API_KEY = os.getenv("SP156_API_KEY", "")\n' > api/app/config_demo.py
        git add api/app/config_demo.py
        git commit -m "demo: chave lida de variável de ambiente"
        git push --force-with-lease
        ;;
      demo/dependencia-vulneravel)
        sed -i.bak '/^urllib3==1.26.4$/d' api/requirements.txt && rm -f api/requirements.txt.bak
        git commit -am "demo: remove dependência vulnerável"
        git push
        ;;
      *)
        echo "Rode 'corrigir' de dentro de uma branch demo/*." >&2
        exit 1
        ;;
    esac
    echo "Veja o Actions: a nova execução deve passar. Print do antes e depois."
    echo "Depois: git switch main && git branch -D ${branch} && git push origin --delete ${branch}"
    ;;
  *)
    sed -n '2,10p' "$0"
    exit 1
    ;;
esac
