import argparse, csv, os, sys
from pathlib import Path
import psycopg
from dotenv import load_dotenv

COLUMNS = {
 "territories": ["territory_id","name","territory_type","country_code","parent_territory_id","description","boundary_source_url"],
 "sources": ["source_id","publisher","title","source_type","url","published_date","accessed_at","notes"],
 "policy_changes": ["policy_id","territory_id","title","policy_type","summary","announcement_date","adoption_date","effective_date","end_date","status","affected_sector","expected_mechanism","source_id","official_reference"],
 "companies": ["company_id","name","legal_name","country_code","sector","ticker","lei","registry_id","headquarters_territory_id","website_url","notes"],
 "company_indicators": ["indicator_id","company_id","territory_id","indicator_code","period_start","period_end","value","unit","currency","geographic_scope","source_id","source_page","notes"],
 "company_exposures": ["exposure_id","company_id","territory_id","exposure_type","exposure_score","exposure_basis","source_id","source_page","start_date","end_date","notes"],
 "company_prices": ["company_price_id","company_id","price_date","close_price","adjusted_close_price","volume","currency","source_id","notes"],
 "market_index_prices": ["market_index_price_id","index_name","price_date","close_value","currency","source_id","notes"],
 "territory_indicators": ["territory_indicator_id","territory_id","indicator_code","period_start","period_end","value","unit","geographic_scope","source_id","source_page","notes"]
}
KEYS = {"territories":"territory_id","sources":"source_id","policy_changes":"policy_id","companies":"company_id","company_indicators":"indicator_id","company_exposures":"exposure_id","company_prices":"company_price_id","market_index_prices":"market_index_price_id","territory_indicators":"territory_indicator_id"}

def main():
    p=argparse.ArgumentParser(description="Importe un CSV GLPID dans PostgreSQL.")
    p.add_argument("csv_file"); p.add_argument("table", choices=sorted(COLUMNS))
    a=p.parse_args(); load_dotenv()
    required=["PGHOST","PGPORT","PGDATABASE","PGUSER","PGPASSWORD"]
    missing=[x for x in required if not os.getenv(x)]
    if missing: sys.exit("Paramètres manquants dans .env : "+", ".join(missing))
    path=Path(a.csv_file)
    if not path.exists(): sys.exit(f"Fichier introuvable : {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: sys.exit("CSV sans en-têtes.")
        cols=reader.fieldnames
        bad=set(cols)-set(COLUMNS[a.table])
        if bad: sys.exit("Colonnes inconnues : "+", ".join(sorted(bad)))
        rows=[]
        for r in reader:
            r={k:(v.strip() if v else None) for k,v in r.items()}
            if any(r.values()): rows.append(r)
    if not rows: print("Aucune ligne à importer (fichier vide)."); return
    key=KEYS[a.table]; update=[c for c in cols if c!=key]
    qcols=", ".join('"'+c+'"' for c in cols)
    vals=", ".join(["%s"]*len(cols))
    upd=", ".join('"'+c+'"=EXCLUDED."'+c+'"' for c in update)
    conflict=f'ON CONFLICT ("{key}") DO UPDATE SET {upd}' if upd else f'ON CONFLICT ("{key}") DO NOTHING'
    query=f'INSERT INTO "{a.table}" ({qcols}) VALUES ({vals}) {conflict}'
    connargs=dict(host=os.environ["PGHOST"], port=int(os.environ["PGPORT"]), dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"])
    with psycopg.connect(**connargs) as conn:
        with conn.cursor() as cur:
            for row in rows: cur.execute(query, [row.get(c) for c in cols])
    print(f"{len(rows)} ligne(s) importée(s)/mise(s) à jour dans {a.table}.")
if __name__=="__main__": main()
