#!/usr/bin/env python3
"""Dominican Republic: laws (and resolutions of the Congreso Nacional, and the Constitution)
split out of the yearly compilations of the Gaceta Oficial published by the Biblioteca del
Congreso Nacional (https://bibliotecadelcongreso.gob.do/gaceta.htm — one text PDF per year).

In those volumes every act starts on a new page with a caption such as
  "Ley núm. 1-23 que autoriza ... G. O. No. 11095 del 17 de enero de 2023."
which is used to segment the volume. Executive decrees ("Dec. núm.") and other acts are
skipped (counted). Each volume is downloaded, verified, text-extracted, then deleted.

Usage: do_fetch.py [extract|convert|all]
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date

import requests
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import do_pdfmd as P  # noqa: E402

RAW = os.environ.get("RAW", "/Users/magicaltux/projects/lawcodex/_raw/do")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
SITE = "https://bibliotecadelcongreso.gob.do/"
TODAY = date.today().isoformat()
MIN_YEAR = int(os.environ.get("DO_MIN_YEAR", "1990"))
MESES = {m: i + 1 for i, m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}
s = requests.Session()
s.headers["User-Agent"] = UA

CAPTION = re.compile(r"^(?:(?:Ley|Resoluci[óo]n|Decreto|Reglamento|Acuerdo|Fe de errata|Contrato|Convenio|"
                     r"Tratado|Sentencia|Aviso|Norma)\b|(?:Res|Dec|P\.E)\s*\.)")  # case-sensitive: captions are capitalised
NUM = re.compile(r"(?:N\s*[oº°]\s*s?\.?|n[úu]m\.?)\s*(\d+)\s*-\s*(\d{2,4})", re.I)


def volumes():
    html = s.get(SITE + "gaceta.htm", timeout=60).content.decode("utf-8", "replace")
    vols = set(re.findall(r'href="(gaceta/Gaceta_oficial_(\d{4})\.pdf)"', html))
    # newest first; volumes before MIN_YEAR are large scanned compilations (no text layer)
    return sorted((v for v in vols if int(v[1]) >= MIN_YEAR), key=lambda x: x[1], reverse=True)


def extract():
    d = os.path.join(RAW, "vol")
    os.makedirs(d, exist_ok=True)
    for href, year in volumes():
        out = os.path.join(d, f"{year}.json")
        if os.path.exists(out):
            continue
        tmp = os.path.join(RAW, f"tmp-{year}.pdf")
        ok = False
        for k in range(3):
            with s.get(SITE + href, timeout=(30, 1800), stream=True) as r:
                if r.status_code != 200:
                    break
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if P.pdf_ok(tmp):
                ok = True
                break
            time.sleep(30)
        if not ok:
            json.dump({"error": "download failed"}, open(out, "w"))
            continue
        pages = P.extract_pages(tmp)
        os.remove(tmp)
        json.dump({"year": year, "url": SITE + href, "pages": pages}, open(out, "w"), ensure_ascii=False)
        txt = sum(1 for t in pages if len(t.strip()) > 200)
        print(year, len(pages), "pages", txt, "with text", flush=True)
        time.sleep(5)


def first_lines(t, n=8):
    ls = [l.strip() for l in t.split("\n") if l.strip()]
    ls = [l for l in ls if not re.fullmatch(r"-\s*\d+\s*-|_{5,}", l)]
    return ls[:n]


def slug(t, n=70):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].rstrip("-")


def segment(pages):
    """Yield (caption, issue_date, [page texts]) for each act. An act starts on a page whose first
    line is a caption ("Ley No. 1-05 que ...") followed by "EL CONGRESO NACIONAL" or a
    "G. O. No." reference; a new Gaceta issue (cover page with ÍNDICE) closes the current act."""
    cur, cap, cap_date, issue_date = [], None, None, None
    for t in pages:
        fl = first_lines(t, 16)
        head = " ".join(fl[:6])
        upper = " ".join(fl).upper()
        starts = bool(fl) and CAPTION.match(fl[0]) and (re.search(r"G\.\s*O\.\s*(No|núm)", head, re.I)
                                                       or "CONGRESO NACIONAL" in upper
                                                       or NUM.search(fl[0][:45]))
        issue = bool(fl) and (re.match(r"AÑO\s+[CLXVI]+", fl[0]) or "GACETA OFICIAL" in head[:200])
        if issue:
            m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de[l]?\s+(\d{4})", " ".join(l for l in fl[:14] if "Fundada" not in l))
            if m and m.group(2).lower() in MESES:
                issue_date = f"{m.group(3)}-{MESES[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
        if starts or issue:
            if cap:
                yield cap, cap_date, cur
            cap, cur = (head if starts else None), []
            cap_date = issue_date
            if issue:
                # an issue entirely devoted to the Constitution (e.g. G.O. 10561 of 2010, 10805 of 2015)
                if any(re.fullmatch(r"CONSTITUCI[ÓO]N( DE LA REP[ÚU]BLICA( DOMINICANA)?)?", l.upper()) for l in fl[:14]):
                    m = re.match(r"AÑO\s+[CLXVI]+\s+(\d+)", fl[0])
                    cap = "Constitución de la República Dominicana" + (f" G. O. No. {m.group(1)}" if m else "")
                continue
        if cap:
            cur.append(t)
    if cap:
        yield cap, cap_date, cur


def convert():
    st = {"leyes": 0, "resoluciones": 0, "constitucion": 0, "skipped_other": 0}
    used = set()
    seen_vols = set()
    for f in sorted(os.listdir(os.path.join(RAW, "vol")), reverse=True):
        v = json.load(open(os.path.join(RAW, "vol", f)))
        if not v.get("pages"):
            continue
        sig = hash("".join(v["pages"][:3]))
        if sig in seen_vols:  # the library's 1990 file is a copy of 1991
            continue
        seen_vols.add(sig)
        for cap, issue_date, pgs in segment(v["pages"]):
            m = re.match(r"(.*?G\.\s*O\.\s*(?:No\.?|núm\.?)\s*([\d-]+)\s*(?:del?|,)?\s*(\d{1,2})\s+de\s+(\w+)\s+de[l]?\s+(\d{4}))", cap, re.I)
            caption = re.sub(r"\s+", " ", m.group(1) if m else cap).strip()
            caption = re.split(r"\s+(?:EL CONGRESO NACIONAL|EN NOMBRE DE LA REP|En Nombre de la Rep|LA ASAMBLEA NACIONAL)", caption)[0]
            if re.match(r"Ley", caption, re.I):
                folder, typ = "leyes", "act"
            elif re.match(r"Res(\.|oluci)", caption, re.I) and pgs and "CONGRESO NACIONAL" in pgs[0][:3000].upper():
                folder, typ = "resoluciones", "resolution"
            elif caption.startswith("Constitución de la República Dominicana"):
                folder, typ = "constitucion", "constitution"
            else:
                st["skipped_other"] += 1
                continue
            iso = None
            if m and m.group(4).lower() in MESES:
                iso = f"{m.group(5)}-{MESES[m.group(4).lower()]:02d}-{int(m.group(3)):02d}"
            mnum = NUM.search(caption[:80])
            num = f"{mnum.group(1)}-{mnum.group(2)}" if mnum else None
            iso = iso or issue_date
            year = (iso or v["year"])[:4]
            name = f"{folder}/{year}/" + (f"{folder[:-1] if folder != 'leyes' else 'ley'}-{slug(num, 20)}" if num else slug(caption, 60)) + ".md"
            if folder == "constitucion":
                name = f"constitucion/constitucion-{year}.md"
            k = 2
            while name in used:
                name = re.sub(r"(-v\d+)?\.md$", f"-v{k}.md", name)
                k += 1
            used.add(name)
            # drop the caption lines (repeated as title) from the first page
            body = P.clean_pages(pgs, head_n=2, foot_n=1)
            md = P.lines_to_md(body)
            if folder == "constitucion" and md.count("###### ") < 20:
                st["skipped_other"] += 1  # e.g. scanned issue: no usable text
                used.discard(name)
                continue
            gaceta = f"G. O. No. {m.group(2)}" if m else None
            title = re.sub(r"\s*G\.\s*O\..*$", "", caption).strip().rstrip(".")
            front = {"title": title, "identifier": (f"Ley núm. {num}" if folder == "leyes" else f"Res. núm. {num}") if num else None,
                     "type": typ, "jurisdiction": "do", "language": "es", "date": iso, "gaceta_oficial": gaceta,
                     "status": "unknown", "source": v["url"], "retrieved": TODAY}
            fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, width=1000).strip()
            path = os.path.join(REPO, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write("\n".join(["---", fm, "---", "", f"# {title}", "",
                f"> Texto publicado en la Gaceta Oficial ({gaceta or 'compilación anual'}), según la compilación anual de la "
                "Biblioteca del Congreso Nacional; texto original, no consolidado.", "", md, ""]))
            st[folder] += 1
    print(st)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("extract", "all"):
        extract()
    if cmd in ("convert", "all"):
        convert()
