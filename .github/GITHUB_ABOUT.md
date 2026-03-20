# GitHub “About” section

Set this on **github.com → your repo → Code** tab, then click the **⚙️ gear** next to **About** (or use the GitHub CLI below).

## Suggested description (paste into Description)

**Streamlit MVP:** If an iBuyer bought this house today, would they make money? Uses Zillow ZHVI + days on market by metro, ZIP→metro via Census CBSA / county, and a simple offer engine (fees, hold, risk).

*(Short version if you hit a character limit:)*  
**iBuyer-style deal checker — Zillow ZHVI by metro, ZIP→CBSA mapping, Streamlit UI.**

## Website

**Live app:** https://openhouse-ai-2hmegkbyadye8uab8l3iua.streamlit.app/

Paste that into the **Website** field in About (or use `--homepage` in the `gh` command below).

## Suggested topics

Add any subset of:

`streamlit` · `python` · `real-estate` · `zillow` · `housing` · `data-science` · `pandas` · `pgeocode` · `census-data` · `ibuyer` · `mortgage`

## One command (GitHub CLI)

If you use [`gh`](https://cli.github.com/):

```bash
gh auth login   # once

gh repo edit dstrunin/Openhouse-Ai \
  --description "Streamlit MVP: iBuyer-style profitability check using Zillow ZHVI, ZIP→metro (Census CBSA), and an offer engine." \
  --homepage "https://openhouse-ai-2hmegkbyadye8uab8l3iua.streamlit.app/" \
  --add-topic streamlit --add-topic python --add-topic zillow \
  --add-topic real-estate --add-topic housing --add-topic data-science
```
