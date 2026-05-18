from __future__ import annotations

import logging
import sys
import sqlite3 
import pandas as pd
import streamlit as st

from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent.parent))
from src.db import save_project, save_floor_plan
from src.models import HousePlanParsed, ParsedRoom
from src.services.vision import VisionParseError, house_plan_result


logger = logging.getLogger(__name__)

st.set_page_config(page_title="Upload Denah", page_icon="📐", layout="wide")
st.title("📐 Upload Denah")
st.caption(
    "Upload foto/scan denah interior. AI akan mendeteksi ruangan & dimensinya. "
    "Kamu bisa edit hasilnya sebelum lanjut ke generate RAB."
)

# ============================================================
# Session state init
# ============================================================
if "parse_result" not in st.session_state:
    st.session_state.parse_result = None  # type: HousePlanParsed | None
if "rooms_df" not in st.session_state:
    st.session_state.rooms_df = None  # type: pd.DataFrame | None


def _result_to_df(result: HousePlanParsed) -> pd.DataFrame:
    """Convert hasil parsing ke DataFrame untuk st.data_editor."""
    return pd.DataFrame(
        [
            {
                "name": r.name,
                "length": r.length,
                "width": r.width,
                "confidence": r.confidence,
                "notes": r.notes or "",
            }
            for r in result.rooms
        ]
    )


def _df_to_rooms_list(df: pd.DataFrame) -> list[ParsedRoom]:
    """Convert hasil edit DataFrame balik ke list Pydantic objects.

    Validasi via Pydantic — kalau user input invalid (mis. dimensi 0),
    Pydantic akan raise ValidationError yang kita catch di caller.
    """
    rows: list[ParsedRoom] = []
    for _, row in df.iterrows():
        # Skip baris yang kosong (user hapus via data_editor)
        if pd.isna(row.get("name")) or not str(row.get("name", "")).strip():
            continue
        rows.append(
            ParsedRoom(
                name=str(row["name"]),
                length=float(row["length"]),
                width=float(row["width"]),
                confidence=row.get("confidence") or "medium",
                notes=str(row["notes"]) if row.get("notes") else None,
            )
        )
    return rows


# ============================================================
# Section 1: Upload
# ============================================================
st.subheader("1. Upload Foto Denah")

uploaded = st.file_uploader(
    "Pilih file (JPG/PNG, max 10 MB)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
)

col_upload_left, col_upload_right = st.columns([1, 1])

if uploaded is not None:
    # Validasi ukuran file
    file_size_mb = len(uploaded.getvalue()) / (1024 * 1024)
    if file_size_mb > 10:
        st.error(f"File terlalu besar ({file_size_mb:.1f} MB). Maksimal 10 MB.")
        st.stop()

    with col_upload_left:
        st.image(uploaded, caption=f"Preview: {uploaded.name}", use_container_width=True)

    with col_upload_right:
        st.info(f"📁 **{uploaded.name}** — {file_size_mb:.2f} MB")
        if st.button("🤖 Parse dengan AI", type="primary", use_container_width=True):
            try:
                with st.spinner("AI sedang membaca denah... (10-30 detik)"):
                    image_bytes = uploaded.getvalue()
                    result = house_plan_result(image_bytes)
                    st.session_state.parse_result = result
                    st.session_state.rooms_df = _result_to_df(result)
                st.success(f"✅ Berhasil deteksi {len(result.rooms)} ruangan")
                st.rerun()
            except VisionParseError as e:
                logger.exception("Parse gagal")
                st.error(f"❌ Gagal parse denah: {e}")
                st.info("💡 Coba foto yang lebih jelas, atau pakai **Input Manual** di bawah.")

# ============================================================
# Section 2: Edit hasil parsing
# ============================================================
if st.session_state.rooms_df is not None:
    st.divider()
    st.subheader("2. Review & Edit Ruangan")

    result: HousePlanParsed = st.session_state.parse_result

    # Info dari LLM
    if result.scale:
        st.caption(f"📏 Skala terdeteksi: `{result.scale}`")
    for warning in result.warnings:
        st.warning(f"⚠️ {warning}")

    st.caption(
        "💡 Edit nama, dimensi, atau hapus baris langsung di tabel. "
        "Tambah baris dengan klik baris kosong di bawah."
    )

    edited_df = st.data_editor(
        st.session_state.rooms_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Ruangan", required=True),
            "length": st.column_config.NumberColumn(
                "Panjang (m)", min_value=0.1, max_value=50.0, step=0.1, format="%.2f"
            ),
            "width": st.column_config.NumberColumn(
                "Lebar (m)", min_value=0.1, max_value=50.0, step=0.1, format="%.2f"
            ),
            "confidence": st.column_config.SelectboxColumn(
                "Confidence",
                options=["high", "medium", "low"],
                help="Tingkat keyakinan AI terhadap dimensi",
            ),
            "notes": st.column_config.TextColumn("Catatan", help="Opsional"),
        },
        key="ruangan_editor",
    )

    # ============================================================
    # Section 3: Konfirmasi
    # ============================================================
    st.divider()
    st.subheader("3. Konfirmasi Data")

    col_input_left, col_input_right = st.columns(2)
    with col_input_left:
        project_name = st.text_input("Nama proyek", placeholder="Contoh: Rumah Pak Budi - Renovasi")
    with col_input_right:
        project_location = st.text_input("Lokasi proyek", value="Malang, Jawa Timur")

    if st.button("✅ Konfirmasi & Lanjut ke RAB", type="primary"):
        if not project_name.strip():
            st.error("Nama proyek wajib diisi.")
            st.stop()

        try:
            rooms_list = _df_to_rooms_list(edited_df)
            if not rooms_list:
                st.error("Minimal harus ada 1 ruangan.")
                st.stop()
        except Exception as e:
            st.error(f"Data tidak valid: {e}")
            st.stop()

        # Rebuild HousePlanParsed dari data yang sudah di-edit user
        # (kita simpan versi edited ke DB, bukan versi mentah dari AI)
        try:
            parsed = HousePlanParsed(
                rooms=rooms_list,
                scale=result.scale,
                warnings=result.warnings,
            )
        except Exception as e:
            st.error(f"Validasi denah gagal: {e}")
            st.stop()

        # Persist ke DB
        try:
            project_id = save_project(project_name.strip(), project_location.strip())
            save_floor_plan(project_id, parsed)
        except sqlite3.Error as e:
            logger.exception("DB save failed")
            st.error(f"❌ Gagal simpan ke database: {e}")
            st.stop()

        # Simpan project_id ke session — dipakai page RAB untuk fetch data
        st.session_state.project_id = project_id
        st.session_state.confirmed_project = {
            "project_name": project_name.strip(),
            "project_location": project_location.strip(),
            "rooms": [r.model_dump() for r in rooms_list],
        }

        total_luas = sum(r.length * r.width for r in rooms_list)
        st.success(
            f"✅ Tersimpan ke DB (project #{project_id}): "
            f"**{len(rooms_list)} ruangan**, total luas **{total_luas:.2f} m²**."
        )
        st.info("Lanjutkan ke halaman **📊 RAB** dari sidebar untuk generate estimasi biaya.")

# ============================================================
# Fallback: Input manual (selalu accessible)
# ============================================================
st.divider()
with st.expander("🖊️ Tidak punya foto denah? Input manual ruangan di sini"):
    st.caption("Mulai dari tabel kosong, isi nama & dimensi tiap ruangan.")

    if st.button("Mulai input manual"):
        empty_df = pd.DataFrame(
            [{"name": "", "length": 3.0, "width": 3.0, "confidence": "high", "notes": ""}]
        )
        st.session_state.parse_result = HousePlanParsed(
            rooms=[ParsedRoom(name="placeholder", length=3.0, width=3.0)],
            scale=None,
            warnings=["Input manual — tidak ada parsing AI"],
        )
        st.session_state.rooms_df = empty_df
        st.rerun()