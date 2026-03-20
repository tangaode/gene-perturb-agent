import argparse
import json
from pathlib import Path

from backend.virtualcell_service.app.dosedirko.io import read_10x_mtx
from backend.virtualcell_service.app.cellgroup import (
    cluster_cells,
    compute_top_markers,
    run_umap,
    annotate_clusters_with_llm,
    save_outputs,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mtx-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n-top-genes", type=int, default=2000)
    ap.add_argument("--resolution", type=float, default=0.5)
    ap.add_argument("--annotate", action="store_true")
    args = ap.parse_args()

    X, genes, barcodes = read_10x_mtx(args.mtx_dir)
    labels, pcs, Xn, adata, qc_summary = cluster_cells(
        X,
        genes,
        barcodes,
        n_top_genes=args.n_top_genes,
        resolution=args.resolution,
    )
    markers, marker_table = compute_top_markers(
        adata,
        llm_top_n=100,
        sig_p_cutoff=0.05,
        sig_logfc_cutoff=0.5,
    )
    um = run_umap(adata)

    if args.annotate:
        cell_map = annotate_clusters_with_llm(markers)
    else:
        cell_map = {int(k): f"cluster_{k}" for k in markers.keys()}

    save_outputs(args.out_dir, adata, labels, um, markers, marker_table, cell_map, qc_summary)

    # print compact summary for launcher parsing
    uniq = sorted(list(set(labels.tolist())))
    marker_preview = {}
    for c, glist in markers.items():
        marker_preview[int(c)] = glist[:5]

    summary = {
        "out_dir": str(Path(args.out_dir).resolve()),
        "clusters": [
            {
                "cluster": int(c),
                "cell_type": cell_map.get(int(c), f"cluster_{c}"),
                "n_cells": int((labels == c).sum()),
                "top_markers_preview": marker_preview.get(int(c), []),
            }
            for c in uniq
        ],
        "annotation_file": str((Path(args.out_dir) / "cluster_annotations.csv").resolve()),
        "marker_table_file": str((Path(args.out_dir) / "cluster_markers_significant.csv").resolve()),
        "qc_summary_file": str((Path(args.out_dir) / "qc_summary.csv").resolve()),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
