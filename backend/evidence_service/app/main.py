from fastapi import FastAPI

from .schemas import VerifyBatchRequest, VerifyBatchResponse, VerifyReport, EvidenceItem
from .providers.ncbi import evidence_from_ncbi
from .providers.enrichr import get_leading_genes_multi as enrichr_multi
from .providers.gprofiler import get_leading_genes_multi as gprof_multi
from .providers.stringdb import string_ppi_score
from .providers.biogrid import biogrid_ppi_score
from .providers.corum import corum_shared_complex_score

app = FastAPI(title="Evidence Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/verify_batch", response_model=VerifyBatchResponse)
def verify_batch(req: VerifyBatchRequest):
    candidates = req.candidates
    up_genes = [c.gene for c in candidates if c.direction == "up"]
    down_genes = [c.gene for c in candidates if c.direction == "down"]

    enrichr_libs = [
        "GO_Biological_Process_2021",
        "GO_Molecular_Function_2021",
        "GO_Cellular_Component_2021",
        "Reactome_2022",
        "KEGG_2021_Human",
        "WikiPathways_2023_Human",
        "MSigDB_Hallmark_2020",
    ]
    gp_sources = ["GO:BP", "GO:MF", "GO:CC", "REAC", "KEGG", "WP"]

    lead_up = {}
    lead_down = {}
    try:
        lead_up = enrichr_multi(up_genes, enrichr_libs, top_terms=5)
        lead_down = enrichr_multi(down_genes, enrichr_libs, top_terms=5)
    except Exception:
        pass
    try:
        gp_up = gprof_multi(up_genes, sources=gp_sources, top_terms=5)
        gp_down = gprof_multi(down_genes, sources=gp_sources, top_terms=5)
        lead_up.update(gp_up)
        lead_down.update(gp_down)
    except Exception:
        pass

    reports = []
    for c in candidates:
        evidence_rel = 0.0
        evidence_dir = 0.0
        items = []

        try:
            er, ed, its = evidence_from_ncbi(req.input_gene, c.gene, c.direction)
            evidence_rel += er
            evidence_dir += ed
            items.extend(its)
        except Exception:
            pass

        # PPI / complexes
        try:
            s_score, s_items = string_ppi_score(req.input_gene, c.gene)
            evidence_rel += min(0.3, s_score)
            items.extend(s_items)
        except Exception:
            pass
        try:
            b_score, b_items = biogrid_ppi_score(req.input_gene, c.gene)
            evidence_rel += min(0.2, b_score)
            items.extend(b_items)
        except Exception:
            pass
        try:
            c_score, c_items = corum_shared_complex_score(req.input_gene, c.gene)
            evidence_rel += min(0.2, c_score)
            items.extend(c_items)
        except Exception:
            pass

        # Enrichment direction evidence
        if c.direction == "up":
            for lib, genes in lead_up.items():
                if c.gene in genes:
                    evidence_rel += 0.05
                    evidence_dir += 0.05
                    items.append({"source": lib, "text": "gene in UP leading set", "meta": {"gene": c.gene}})
        else:
            for lib, genes in lead_down.items():
                if c.gene in genes:
                    evidence_rel += 0.05
                    evidence_dir += 0.05
                    items.append({"source": lib, "text": "gene in DOWN leading set", "meta": {"gene": c.gene}})

        evidence_rel = min(1.0, evidence_rel)
        evidence_dir = min(1.0, evidence_dir)

        reports.append(VerifyReport(
            gene=c.gene,
            direction=c.direction,
            evidence_rel=evidence_rel,
            evidence_dir=evidence_dir,
            items=[EvidenceItem(**i) if isinstance(i, dict) else i for i in items[:3]],
        ))

    return VerifyBatchResponse(reports=reports)
