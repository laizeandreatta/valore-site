#!/usr/bin/env python3
"""Gera o site público da Valore Imobiliária a partir do painel.

Uso:  python3 tools/build.py <pasta-com-o-export-do-painel>
A pasta deve conter imoveis/*.json (export do banco do painel). Esse export
tem dados internos (proprietário, comissão, observações) e NUNCA entra no
repositório: o script copia para o site apenas os campos públicos abaixo.
Fotos e vídeos ficam em src/fotos/<id-do-imovel>/ (01.jpg, 02.jpg..., video.mp4).
"""
import json, os, re, shutil, sys, html, glob, datetime
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")
SRC = os.path.join(ROOT, "src")
CFG = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))
DOM = CFG["dominio"]
BASE = "https://" + DOM

PUBLIC_STATUS_OUT = {"Vendido", "Inativo", "Desistiu", "Suspenso", "Retirado"}


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def slugify(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def brl(v):
    if not v:
        return "Sob consulta"
    return "R$ " + f"{int(round(v)):,}".replace(",", ".")


def num(v):
    if v in (None, ""):
        return None
    f = float(v)
    return int(f) if f.is_integer() else round(f, 2)


def m2(v):
    v = num(v)
    if v is None:
        return ""
    return (f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")) + " m²"


def public_street(end, regiao):
    """Rua sem número, sem CEP e sem unidade."""
    if not end:
        return regiao or ""
    parts = [p.strip() for p in end.split(",")]
    rua = parts[0]
    rua = re.sub(r"\s+\d+.*$", "", rua)
    return rua


def wa_link(msg):
    n = re.sub(r"\D", "", CFG.get("whatsapp") or "")
    if not n:
        return None
    if not n.startswith("55"):
        n = "55" + n
    from urllib.parse import quote
    return f"https://wa.me/{n}?text={quote(msg)}"


def load(db):
    items = []
    for f in sorted(glob.glob(os.path.join(db, "imoveis", "*.json"))):
        doc = json.load(open(f, encoding="utf-8"))
        d = doc.get("data", doc)
        iid = doc.get("id") or os.path.splitext(os.path.basename(f))[0]
        if (d.get("noSite") or "Sim") != "Sim" or d.get("status") in PUBLIC_STATUS_OUT:
            continue
        titulo = d.get("tituloSite") or re.sub(r"\s*·\s*(apto|ap\.?|unidade)?\s*\d+.*$", "", d.get("titulo", ""), flags=re.I)
        predio = (d.get("empreendimento") or d.get("titulo") or "").split("·")[0].strip()
        fotos = sorted(glob.glob(os.path.join(SRC, "fotos", iid, "[0-9]*.jpg")))
        video = os.path.join(SRC, "fotos", iid, "video.mp4")
        items.append({
            "id": iid,
            "slug": slugify((d.get("codigo") or "") + " " + predio),
            "codigo": d.get("codigo", ""),
            "titulo": titulo,
            "predio": predio,
            "regiao": d.get("regiao", ""),
            "tipo": d.get("tipo", "Apartamento"),
            "rua": public_street(d.get("endereco", ""), d.get("regiao")),
            "cidade": "Balneário Camboriú" if d.get("regiao") == "Balneário Camboriú" else "Itajaí",
            "valor": num(d.get("valor")) or 0,
            "area": num(d.get("area")),
            "quartos": num(d.get("quartos")),
            "suites": num(d.get("suites")),
            "vagas": num(d.get("vagas")),
            "andar": d.get("andar", ""),
            "texto": d.get("textoSite", ""),
            "destaques": [x.strip() for x in (d.get("destaques") or "").split("·") if x.strip()],
            "fotos_src": fotos,
            "video_src": video if os.path.exists(video) else None,
            "criado": d.get("criadoEm", ""),
        })
    items.sort(key=lambda x: (len(x["fotos_src"]) == 0, x["codigo"]))
    return items


def process_media(it):
    dst = os.path.join(OUT, "fotos", it["slug"])
    os.makedirs(dst, exist_ok=True)
    fotos = []
    for i, f in enumerate(it["fotos_src"], 1):
        im = Image.open(f).convert("RGB")
        w, h = im.size
        big = im.copy(); big.thumbnail((1800, 1800), Image.LANCZOS)
        big.save(os.path.join(dst, f"{i:02d}.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
        sm = im.copy(); sm.thumbnail((720, 720), Image.LANCZOS)
        sm.save(os.path.join(dst, f"{i:02d}-p.jpg"), "JPEG", quality=76, optimize=True, progressive=True)
        fotos.append({"g": f"/fotos/{it['slug']}/{i:02d}.jpg", "p": f"/fotos/{it['slug']}/{i:02d}-p.jpg", "w": big.size[0], "h": big.size[1]})
    it["fotos"] = fotos
    it["video"] = None
    if it["video_src"]:
        # vídeos vão para o site sempre sem áudio
        import subprocess
        out = os.path.join(dst, "video.mp4")
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", it["video_src"], "-c:v", "copy", "-an", out])
        if r.returncode != 0:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", it["video_src"], "-an", "-c:v", "libx264", "-crf", "26", "-movflags", "+faststart", out], check=True)
        it["video"] = f"/fotos/{it['slug']}/video.mp4"


ICON = {
    "area": '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 15v5h-5M4 4l6 6M20 20l-6-6"/></svg>',
    "quartos": '<svg viewBox="0 0 24 24"><path d="M3 18v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6M3 15h18M6 10V7a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3M3 18v2M21 18v2"/></svg>',
    "suites": '<svg viewBox="0 0 24 24"><path d="M4 12h16v2a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-2ZM6 12V6a2 2 0 0 1 2-2h1a2 2 0 0 1 2 2M8 19l-1 2M16 19l1 2"/></svg>',
    "vagas": '<svg viewBox="0 0 24 24"><path d="M5 16V11l2-5h10l2 5v5M3 16h18v3H3zM7 11h10"/></svg>',
    "wa": '<svg viewBox="0 0 24 24" class="fill"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.4-.2Z"/></svg>',
    "pin": '<svg viewBox="0 0 24 24"><path d="M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12Z"/><circle cx="12" cy="9" r="2.5"/></svg>',
    "play": '<svg viewBox="0 0 24 24" class="fill"><path d="M8 5v14l11-7z"/></svg>',
    "back": '<svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg>',
}


def specs(it, cls="specs"):
    out = []
    if it["area"]:
        out.append(f'<li>{ICON["area"]}<span>{e(m2(it["area"]))}</span></li>')
    if it["quartos"]:
        out.append(f'<li>{ICON["quartos"]}<span>{it["quartos"]} quarto{"s" if it["quartos"] != 1 else ""}</span></li>')
    if it["suites"]:
        out.append(f'<li>{ICON["suites"]}<span>{it["suites"]} suíte{"s" if it["suites"] != 1 else ""}</span></li>')
    if it["vagas"]:
        out.append(f'<li>{ICON["vagas"]}<span>{it["vagas"]} vaga{"s" if it["vagas"] != 1 else ""}</span></li>')
    return f'<ul class="{cls}">' + "".join(out) + "</ul>"


def media_cover(it, cls="cover", eager=False):
    if it["fotos"]:
        f = it["fotos"][0]
        return f'<img class="{cls}" src="{f["p"]}" alt="{e(it["titulo"])}" width="{f["w"]}" height="{f["h"]}" loading="{"eager" if eager else "lazy"}">'
    return f'<div class="{cls} ph"><img src="/assets/sym_light.png" alt=""><span>Fotos em breve</span></div>'


def head(title, desc, path, og_img=None):
    og = og_img or "/assets/og.jpg"
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Valore Imobiliária">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{BASE}{og}">
<meta name="theme-color" content="#233332">
<link rel="icon" href="/assets/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@200;300;400;500;600&display=swap">
<link rel="stylesheet" href="/assets/site.css?v={VER}">
</head>
<body>
"""


def topbar(active=""):
    wa = wa_link(CFG["whatsappTexto"])
    cta = f'<a class="btn btn-sm" href="{e(wa)}" target="_blank" rel="noopener">{ICON["wa"]}<span>WhatsApp</span></a>' if wa else '<a class="btn btn-sm" href="/#contato">Contato</a>'
    return f"""<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="/" aria-label="Valore Imobiliária, início"><img src="/assets/logo_dark.png" alt="Valore Imobiliária" width="560" height="144"></a>
    <nav class="nav" aria-label="Principal">
      <a href="/#imoveis"{' aria-current="page"' if active=='imoveis' else ''}>Imóveis</a>
      <a href="/#regioes">Regiões</a>
      <a href="/#valore">A Valore</a>
      <a href="/#contato">Contato</a>
    </nav>
    {cta}
  </div>
</header>
"""


def footer():
    wa = wa_link(CFG["whatsappTexto"])
    contatos = []
    if wa:
        contatos.append(f'<a href="{e(wa)}" target="_blank" rel="noopener">WhatsApp</a>')
    if CFG.get("email"):
        contatos.append(f'<a href="mailto:{e(CFG["email"])}">{e(CFG["email"])}</a>')
    if CFG.get("instagram"):
        ig = CFG["instagram"].lstrip("@")
        contatos.append(f'<a href="https://instagram.com/{e(ig)}" target="_blank" rel="noopener">@{e(ig)}</a>')
    creci = f'<p class="fine">CRECI {e(CFG["creci"])}</p>' if CFG.get("creci") else ""
    return f"""<footer class="foot">
  <div class="wrap foot-in">
    <div><img class="foot-logo" src="/assets/logo_light.png" alt="Valore Imobiliária" width="560" height="144">
      <p class="foot-reg">Praia Brava · Balneário Camboriú · Itajaí · Fazenda</p></div>
    <div class="foot-links">{''.join(contatos)}</div>
  </div>
  <div class="wrap foot-base"><p class="fine">© {datetime.date.today().year} Valore Imobiliária. Valores e disponibilidade sujeitos a confirmação.</p>{creci}</div>
</footer>
<script src="/assets/site.js?v={VER}" defer></script>
</body>
</html>
"""


def card(it):
    href = f"/imovel/{it['slug']}/"
    return f"""<article class="card" data-regiao="{e(it['regiao'])}" data-quartos="{it['quartos'] or 0}" data-valor="{it['valor'] or 0}" data-area="{it['area'] or 0}" data-ord="{e(it['codigo'])}">
  <a href="{href}" class="card-link" aria-label="{e(it['titulo'])}">
    <div class="card-media">{media_cover(it)}<span class="tag">{e(it['regiao'])}</span></div>
    <div class="card-body">
      <p class="eb">{e(it['codigo'])} · {e(it['tipo'])}</p>
      <h3>{e(it['titulo'])}</h3>
      {specs(it)}
      <p class="price">{e(brl(it['valor']))}</p>
    </div>
  </a>
</article>"""


def index(items):
    regs = sorted({i["regiao"] for i in items if i["regiao"]})
    reg_opts = "".join(f'<option value="{e(r)}">{e(r)}</option>' for r in regs)
    cards = "\n".join(card(i) for i in items)
    regioes = "".join(
        f'<li><h3>{e(r["nome"])}</h3><p>{e(r["linha"])}</p><a class="lnk" href="#imoveis" data-goreg="{e(r["nome"])}">Ver imóveis</a></li>'
        for r in CFG["regioes"])
    wa = wa_link(CFG["whatsappTexto"])
    contato_btn = (f'<a class="btn btn-light" href="{e(wa)}" target="_blank" rel="noopener">{ICON["wa"]}<span>Conversar pelo WhatsApp</span></a>'
                   if wa else (f'<a class="btn btn-light" href="mailto:{e(CFG["email"])}">Enviar e-mail</a>' if CFG.get("email") else ""))
    desc = "Apartamentos selecionados na Praia Brava, em Balneário Camboriú e em Itajaí, com assessoria jurídica do primeiro contato à escritura."
    og = items[0]["fotos"][0]["g"] if items and items[0]["fotos"] else None
    return head("Valore Imobiliária · Praia Brava, Balneário Camboriú e Itajaí", desc, "/", og) + topbar("imoveis") + f"""
<main id="conteudo">
<section class="hero">
  <img class="hero-seal" src="/assets/seal_light.png" alt="" width="420" height="427">
  <div class="wrap hero-in">
    <p class="eb eb-light">Praia Brava · Balneário Camboriú · Itajaí</p>
    <h1>Endereços para viver o litoral com calma, beleza e valor.</h1>
    <p class="lede">Uma curadoria de imóveis escolhidos um a um, com acompanhamento jurídico do primeiro contato à escritura.</p>
    <div class="hero-cta"><a class="btn btn-light" href="#imoveis">Ver imóveis</a>{('<a class="btn btn-ghost" href="#contato">Falar com a Valore</a>')}</div>
  </div>
</section>

<section class="sec" id="imoveis">
  <div class="wrap">
    <div class="sec-h">
      <div><p class="eb">Carteira</p><h2>Imóveis à venda</h2></div>
      <p class="count" id="count">{len(items)} imóve{'is' if len(items)!=1 else 'l'}</p>
    </div>
    <form class="filters" id="filters" onsubmit="return false">
      <label><span>Região</span><select name="regiao"><option value="">Todas</option>{reg_opts}</select></label>
      <label><span>Quartos</span><select name="quartos"><option value="0">Qualquer</option><option value="1">1 ou mais</option><option value="2">2 ou mais</option><option value="3">3 ou mais</option><option value="4">4 ou mais</option></select></label>
      <label><span>Valor</span><select name="valor"><option value="">Qualquer</option><option value="0-1000000">Até R$ 1 milhão</option><option value="1000000-2000000">R$ 1 a 2 milhões</option><option value="2000000-4000000">R$ 2 a 4 milhões</option><option value="4000000-">Acima de R$ 4 milhões</option></select></label>
      <label><span>Ordenar</span><select name="ord"><option value="">Mais recentes</option><option value="vmenor">Menor valor</option><option value="vmaior">Maior valor</option><option value="area">Maior área</option></select></label>
    </form>
    <div class="grid" id="grid">
{cards}
    </div>
    <p class="none" id="none" hidden>Nenhum imóvel com esses filtros por enquanto. Fale com a gente: novos endereços chegam toda semana.</p>
  </div>
</section>

<section class="sec sec-alt" id="regioes">
  <div class="wrap">
    <div class="sec-h"><div><p class="eb">Onde atuamos</p><h2>Três regiões, conhecidas de perto</h2></div></div>
    <ul class="regs">{regioes}</ul>
  </div>
</section>

<section class="sec" id="valore">
  <div class="wrap about">
    <div class="about-mark"><img src="/assets/sym_dark.png" alt="" width="200" height="280"></div>
    <div>
      <p class="eb">A Valore</p>
      <h2>Compra segura, conduzida por quem entende de imóvel e de contrato.</h2>
      <p>A Valore Imobiliária é conduzida por corretores que vivem a Praia Brava e conhecem de perto cada rua, cada edifício e cada vista que apresentam. A assessoria jurídica faz parte da casa: propostas e contratos são redigidos e revisados por advogada antes de chegarem à sua mesa.</p>
      <p>Cada imóvel da nossa carteira é escolhido pela localização, pela qualidade da construção e pelo potencial de valorização. Você recebe um atendimento próximo e dedicado, da primeira visita à entrega das chaves.</p>
    </div>
  </div>
</section>

<section class="cta" id="contato">
  <div class="wrap cta-in">
    <div><p class="eb eb-light">Contato</p><h2>Conte o que você procura. A gente encontra.</h2>
    <p class="lede">Também recebemos imóveis para venda na Praia Brava, em Balneário Camboriú e em Itajaí.</p></div>
    <div class="cta-act">{contato_btn}</div>
  </div>
</section>
</main>
""" + footer()


def detail(it):
    wa = wa_link(f"Olá! Tenho interesse no imóvel {it['codigo']} · {it['titulo']}, que vi no site da Valore.")
    wa_vis = wa_link(f"Olá! Gostaria de agendar uma visita ao imóvel {it['codigo']} · {it['titulo']}.")
    if it["fotos"]:
        main = it["fotos"][0]
        thumbs = "".join(
            f'<button class="th" data-i="{k}" aria-label="Foto {k+1}"><img src="{f["p"]}" alt="" loading="lazy"></button>'
            for k, f in enumerate(it["fotos"]))
        gal = f"""<div class="gal" id="gal" data-fotos='{e(json.dumps([f["g"] for f in it["fotos"]]))}'>
      <button class="gal-main" data-i="0" aria-label="Ampliar foto"><img src="{main['g']}" alt="{e(it['titulo'])}" width="{main['w']}" height="{main['h']}"></button>
      <div class="gal-strip">{thumbs}</div>
      <p class="gal-n">{len(it['fotos'])} fotos{' · vídeo abaixo' if it['video'] else ''}</p>
    </div>"""
    else:
        gal = f'<div class="gal">{media_cover(it, "gal-ph", True)}</div>'
    video = (f'<section class="blk"><h2>Vídeo</h2><video controls muted playsinline preload="metadata" poster="{it["fotos"][0]["g"] if it["fotos"] else ""}" src="{it["video"]}"></video></section>'
             if it["video"] else "")
    dest = "".join(f"<li>{e(d)}</li>" for d in it["destaques"])
    btn = (f'<a class="btn btn-full" href="{e(wa)}" target="_blank" rel="noopener">{ICON["wa"]}<span>Tenho interesse</span></a>'
           f'<a class="btn btn-full btn-out" href="{e(wa_vis)}" target="_blank" rel="noopener">Agendar visita</a>') if wa else '<a class="btn btn-full" href="/#contato">Tenho interesse</a>'
    loc_q = f"{it['rua']}, {it['regiao']}, {it['cidade']} SC"
    from urllib.parse import quote
    mapa = f'<iframe class="map" title="Mapa" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps?q={quote(loc_q)}&z=15&output=embed"></iframe>'
    desc = it["texto"] or f"{it['tipo']} na {it['regiao']}."
    path = f"/imovel/{it['slug']}/"
    og = it["fotos"][0]["g"] if it["fotos"] else None
    return head(f"{it['titulo']} · {it['regiao']} · Valore Imobiliária", desc[:160], path, og) + topbar() + f"""
<main id="conteudo" class="det">
  <div class="wrap">
    <a class="back" href="/#imoveis">{ICON['back']}<span>Todos os imóveis</span></a>
    {gal}
    <div class="det-grid">
      <div class="det-main">
        <p class="eb">{e(it['codigo'])} · {e(it['tipo'])} · {e(it['regiao'])}</p>
        <h1>{e(it['titulo'])}</h1>
        <p class="addr">{ICON['pin']}<span>{e(it['rua'])}{', ' if it['rua'] and it['rua']!=it['regiao'] else ''}{e(it['regiao'] if it['rua']!=it['regiao'] else '')} · {e(it['cidade'])}/SC</span></p>
        {specs(it, 'specs specs-lg')}
        {f'<section class="blk"><h2>Sobre o imóvel</h2><p class="txt">{e(it["texto"])}</p></section>' if it['texto'] else ''}
        {f'<section class="blk"><h2>Diferenciais</h2><ul class="dest">{dest}</ul></section>' if dest else ''}
        {video}
        <section class="blk"><h2>Localização</h2>{mapa}<p class="fine">Localização aproximada da região.</p></section>
      </div>
      <aside class="det-side">
        <div class="box">
          <p class="eb">Valor de venda</p>
          <p class="price-lg">{e(brl(it['valor']))}</p>
          {specs(it, 'specs specs-sm')}
          {btn}
          <p class="fine">Código {e(it['codigo'])}. Valores e disponibilidade sujeitos a confirmação.</p>
        </div>
      </aside>
    </div>
  </div>
  <div class="lb" id="lb" hidden><button class="lb-x" aria-label="Fechar">×</button><button class="lb-p" aria-label="Anterior">‹</button><img alt=""><button class="lb-n" aria-label="Próxima">›</button><p class="lb-c"></p></div>
  {f'<a class="fab" href="{e(wa)}" target="_blank" rel="noopener" aria-label="WhatsApp">{ICON["wa"]}</a>' if wa else ''}
</main>
""" + footer()


VER = datetime.datetime.now().strftime("%Y%m%d%H%M")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    db = sys.argv[1]
    items = load(db)
    # limpa a saída preservando nada além do que é gerado
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets"))
    for it in items:
        process_media(it)
    for f in glob.glob(os.path.join(SRC, "brand", "*")):
        shutil.copy(f, os.path.join(OUT, "assets"))
    shutil.copy(os.path.join(SRC, "site.css"), os.path.join(OUT, "assets", "site.css"))
    shutil.copy(os.path.join(SRC, "site.js"), os.path.join(OUT, "assets", "site.js"))
    # favicon e og
    sym = Image.open(os.path.join(SRC, "brand", "sym_light.png")).convert("RGBA")
    fav = Image.new("RGBA", (256, 256), (35, 51, 50, 255)); s2 = sym.copy(); s2.thumbnail((150, 150))
    fav.paste(s2, ((256 - s2.size[0]) // 2, (256 - s2.size[1]) // 2), s2); fav.save(os.path.join(OUT, "assets", "favicon.png"))
    og = Image.new("RGB", (1200, 630), (35, 51, 50)); lg = Image.open(os.path.join(SRC, "brand", "logo_light.png")).convert("RGBA")
    lg.thumbnail((640, 640)); og.paste(lg, ((1200 - lg.size[0]) // 2, (630 - lg.size[1]) // 2), lg); og.save(os.path.join(OUT, "assets", "og.jpg"), quality=86)
    # símbolo escuro para fundo claro
    dark = Image.new("RGBA", sym.size, (35, 51, 50, 0)); px = sym.load(); dp = dark.load()
    for y in range(sym.size[1]):
        for x in range(sym.size[0]):
            a = px[x, y][3]; dp[x, y] = (35, 51, 50, a)
    dark.save(os.path.join(OUT, "assets", "sym_dark.png"))

    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index(items))
    for it in items:
        d = os.path.join(OUT, "imovel", it["slug"]); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(detail(it))
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(
        head("Página não encontrada · Valore Imobiliária", "", "/404.html") + topbar() +
        '<main class="nf"><div class="wrap"><p class="eb">404</p><h1>Este endereço não está mais aqui.</h1><p>O imóvel pode ter sido vendido. Veja os disponíveis:</p><a class="btn" href="/#imoveis">Ver imóveis</a></div></main>' + footer())
    open(os.path.join(OUT, "CNAME"), "w").write(DOM + "\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    urls = ["/"] + [f"/imovel/{i['slug']}/" for i in items]
    open(os.path.join(OUT, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{BASE}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    print(f"{len(items)} imóveis publicados:", ", ".join(f"{i['codigo']} ({len(i['fotos'])} fotos)" for i in items))


if __name__ == "__main__":
    main()
