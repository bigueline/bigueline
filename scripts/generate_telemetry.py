"""Snapshot público do GitHub; apenas biblioteca padrão.

Execute: python scripts/generate_telemetry.py
GITHUB_TOKEN é opcional. Falhas preservam o último SVG gerado.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

USERNAME = "bigueline"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "telemetry.svg"


def fetch_json(path):
    """Consulta endpoints públicos, com timeout e token opcional."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bigueline-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_repositories():
    """Inclui todas as páginas, mesmo com mais de 100 repositórios."""
    repositories = []
    page = 1
    while True:
        batch = fetch_json(
            f"/users/{USERNAME}/repos?type=owner&sort=full_name&per_page=100&page={page}"
        )
        repositories.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            return repositories
        page += 1


def render_svg(profile, repositories, collected_at):
    """Barras contam a linguagem principal dos repos públicos sem forks."""
    original = [repo for repo in repositories if not repo["fork"]]
    languages = Counter(repo["language"] for repo in original if repo["language"])
    stars = sum(repo["stargazers_count"] for repo in original)
    metrics = [
        ("01 // GARAGE", len(repositories), "REPOS PÚBLICOS"),
        ("02 // PADDOCK", profile["followers"], "SEGUIDORES"),
        ("03 // PODIUM", stars, "ESTRELAS · SEM FORKS"),
    ]
    cards = []
    for index, (label, value, caption) in enumerate(metrics):
        x = 40 + index * 320
        cards.append(f'''
    <path d="M{x} 122 h280" stroke="#22C55E" stroke-width="2"/>
    <text x="{x}" y="149" class="muted small">{label}</text>
    <text x="{x}" y="201" class="value">{value}</text>
    <text x="{x}" y="231" class="muted small">{caption}</text>''')

    bars = []
    total = sum(languages.values())
    for index, (language, count) in enumerate(languages.most_common(3)):
        y = 320 + index * 39
        width = 400 * count / total
        bars.append(f'''
    <text x="40" y="{y}" class="small">{escape(language)}</text>
    <rect x="220" y="{y - 12}" width="400" height="10" rx="2" fill="#8B949E" opacity="0.18"/>
    <rect x="220" y="{y - 12}" width="{width:.1f}" height="10" rx="2" fill="#22C55E"/>
    <text x="645" y="{y}" class="muted small">{count} / {total} repos</text>''')
    if not bars:
        bars.append('<text x="40" y="330" class="muted small">Nenhuma linguagem identificada nos repos sem forks.</text>')
    timestamp = collected_at.strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="490" viewBox="0 0 1000 490" role="img" aria-labelledby="title desc">
  <title id="title">Telemetria pública de {USERNAME}</title>
  <desc id="desc">Snapshot coletado em {timestamp}: {len(repositories)} repositórios públicos,
    {profile["followers"]} seguidores e {stars} estrelas em repositórios sem forks.
    Barras: até três linguagens principais, por quantidade de repos sem forks com linguagem identificada.
    Atualização diária prevista; não é tempo real.</desc>
  <style>
    text {{ font-family: Consolas, 'Liberation Mono', monospace; fill: #F0F6FC; }}
    .muted {{ fill: #8B949E; }}
    .green {{ fill: #22C55E; }}
    .small {{ font-size: 14px; }}
    .value {{ font-size: 44px; font-weight: bold; }}
  </style>
  <rect width="1000" height="490" rx="12" fill="#0D1117"/>
  <path d="M40 32 h50 m8 0 h18 m8 0 h8" stroke="#22C55E" stroke-width="4"/>
  <text x="40" y="67" font-size="24" font-weight="bold">DEV // TELEMETRY</text>
  <text x="40" y="92" class="muted small">BIGUELINE / PUBLIC GITHUB DATA</text>
  <text x="960" y="65" text-anchor="end" class="green small">V2 // SNAPSHOT</text>
{''.join(cards)}
  <path d="M40 259 H960" stroke="#8B949E" opacity="0.3"/>
  <text x="40" y="290" class="green small">TECH // LINGUAGENS PRINCIPAIS POR REPO</text>
{''.join(bars)}
  <text x="960" y="323" text-anchor="end" class="muted small">SEM FORKS</text>
  <text x="960" y="347" text-anchor="end" class="muted small">TOP 3</text>
  <path d="M40 425 H960" stroke="#8B949E" opacity="0.3"/>
  <text x="40" y="452" class="muted small">COLETA // {timestamp}</text>
  <text x="960" y="452" text-anchor="end" class="green small">BUILDING ONE LAP AT A TIME.</text>
  <text x="40" y="474" class="muted" font-size="12">Atualização diária prevista · Dados da API pública · Não é tempo real</text>
</svg>
'''


def main():
    try:
        profile = fetch_json(f"/users/{USERNAME}")
        repositories = fetch_repositories()
        svg = render_svg(profile, repositories, datetime.now(timezone.utc))
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        # Troca o arquivo final somente depois de concluir a coleta e a escrita.
        temporary = OUTPUT.with_suffix(".tmp")
        temporary.write_text(svg, encoding="utf-8")
        temporary.replace(OUTPUT)
    except (URLError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Falha ao gerar telemetria; SVG anterior preservado: {error}", file=sys.stderr)
        return 1
    print(f"Gerado: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
