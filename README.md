# LawCodex — Dominican Republic (do)

Dominican legislation as Markdown, split out of the **yearly compilations of the Gaceta
Oficial** published by the **Biblioteca del Congreso Nacional** (https://bibliotecadelcongreso.gob.do/gaceta.htm):
the **Constitution** (2010 and 2015 texts), the **laws** (leyes) and the **resolutions of the
Congreso Nacional** (approvals of treaties, loans and contracts) published in the volumes
1991–2023 that have a text layer.

Part of [LawCodex](https://github.com/LawCodex): one public repository per jurisdiction.

Retrieved: **2026-10-13**. Language: Spanish (`es`).

Status: **partial** — see "What is NOT covered".

## What is covered

| Category | Directory | Files |
|---|---|---|
| Constitución de la República Dominicana (proclaimed 26 Jan 2010; 13 Jun 2015 text) | `constitucion/` | 2 |
| Laws (leyes), by year | `leyes/<year>/ley-<n>-<yy>.md` | 803 |
| Resolutions of the Congreso Nacional, by year | `resoluciones/<year>/` | 2,043 |

In the annual volumes every act starts on a new page with a caption ("Ley núm. 1-23 que …
G. O. No. 11095 del 17 de enero de 2023."); the scripts cut each volume at those captions and at
the start of each Gaceta issue. Executive decrees, ministerial resolutions, notices and other
acts of the volumes are skipped (≈6,200 segments). Texts are the **original published texts**
(not consolidated). A few laws appear in two volumes (files with a `-v2` suffix).

## What is NOT covered

- **The 2024 constitutional reform** (proclaimed 27 Oct 2024) and all laws published after
  2023: the library's compilations end with 2023, and the official database of the Consultoría
  Jurídica del Poder Ejecutivo (https://www.consultoria.gov.do/consultas) serves its search API
  behind a Cloudflare JavaScript challenge, which we do not circumvent.
- Volumes 1996, 2002 and 2003 (not offered), and laws before 1990 (the older collections are
  scanned images; no OCR).
- Coverage within a year depends on the library's compilation; laws whose caption could not be
  recognised are missing.
- Codes enacted before 1990 (Código Civil, Código de Comercio, Código Penal, …).

## Source

Biblioteca del Congreso Nacional "Juan Pablo Duarte" — Gaceta oficial, one PDF per year
(`https://bibliotecadelcongreso.gob.do/gaceta/Gaceta_oficial_<year>.pdf`; 0.1–0.8 GB each). Each
file's `source` is the volume, `gaceta_oficial` the issue number when printed in the caption.

## Copyright

Under Dominican Ley N° 65-00 sobre Derecho de Autor, official texts (laws, decrees,
judicial decisions) are not protected; they are reproduced from the official gazette.

## Regenerate

```
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
RAW=/path/to/scratch .venv/bin/python scripts/do_fetch.py all     # downloads ~5 GB of PDFs, one at a time
```
