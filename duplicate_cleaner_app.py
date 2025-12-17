import streamlit as st
import os
from datetime import datetime, timedelta
from duplicate_records_cleaner import DuplicateCleaner

# ------------------------- Badge UI ----------------------------
def colored_badge(count):
    if count == 0:
        color = "#4CAF50"  # green
    elif count < 50:
        color = "#ffa500"  # orange
    else:
        color = "#ff4d4d"  # red

    return f"""
    <span style="
        background-color:{color};
        color:white;
        padding:6px 14px;
        border-radius:12px;
        font-size:15px;
        font-weight:600;
    ">
        {count} duplicates
    </span>
    """

# ------------------------- Page Setup ----------------------------
st.set_page_config(page_title="Mongo Duplicate Cleaner", layout="wide")
st.title("🧹 Mongo Duplicate Cleanup Utility")


# ------------------------- MONGO CONNECTION ----------------------
st.header("1️⃣ Enter MongoDB Connection String")

mongo_uri = st.text_input(
    "MongoDB Connection URI",
    placeholder="mongodb+srv://user:password@cluster.mongodb.net/"
)

if "cleaner" not in st.session_state:
    st.session_state.cleaner = None

# Summaries
st.session_state.setdefault("preview_rows", [])
st.session_state.setdefault("zip_blobs", {})
st.session_state.setdefault("companies", [])


def purge_legacy_zip_files():
    """Remove any zip files from earlier runs so preview does not surface them."""
    prefixes = (
        "live_field_measurement_duplicates",
        "live_production_duplicates",
        "facility_measurement_duplicates",
    )
    try:
        for fname in os.listdir("."):
            if not fname.endswith(".zip"):
                continue
            if "_Vault." in fname or fname.startswith(prefixes):
                os.remove(fname)
    except Exception:
        # Best-effort cleanup; ignore errors so the UI keeps working.
        pass


def dedupe_preview_rows(rows):
    """Return preview rows unique by company to avoid duplicate rendering."""
    unique = {}
    for row in rows:
        company = row.get("company")
        if company:
            unique[company] = row
    return list(unique.values())



# ------------------------- CONNECT BUTTON ------------------------
if st.button("🔌 Connect to Mongo"):
    try:
        cleaner = DuplicateCleaner(connection_string=mongo_uri)
        st.session_state.cleaner = cleaner
        st.session_state.companies = sorted(cleaner.company_ids)
        st.success("Connected successfully!")
        st.info(f"Companies found: {len(cleaner.company_ids)}")
    except Exception as e:
        st.error(f"Connection failed: {e}")


# ------------------------- MAIN WORKFLOW -------------------------
if st.session_state.cleaner:

    cleaner = st.session_state.cleaner

    st.header("2️⃣ Select Companies")
    select_all = st.checkbox("Select all companies")

    if select_all:
        selected_companies = st.session_state.companies
    else:
        selected_companies = st.multiselect(
            "Choose companies to process",
            st.session_state.companies
        )


    st.header("3️⃣ Select Date Range")
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with date_col2:
        end_date = st.date_input("End Date", datetime.now())

    # ==============================================================
    # 4️⃣ COMBINED DUPLICATE OVERVIEW TABLE
    # ==============================================================
    st.markdown("---")
    st.header("4️⃣ Duplicates Table")
    dry_run_mode = st.checkbox("Dry run mode (preview only)", value=True)
    st.caption("Preview (dry run) fills counts. Disable dry run to allow delete.")

    if st.button("🔍 Preview duplicates for selected companies"):
        if not selected_companies:
            st.warning("Select at least one company to preview.")
        else:
            st.session_state.preview_rows = []
            # Clear any prior ZIPs to avoid showing downloads after preview.
            st.session_state.zip_blobs = {}
            purge_legacy_zip_files()
            total = len(selected_companies)
            progress = st.progress(0)

            for idx, company in enumerate(selected_companies):
                cleaner.company_ids = [company]

                fm_summary = cleaner.remove_duplicate_measurements(
                    start_date=str(start_date),
                    dry_run=True,
                    return_summary=True
                )
                lp_summary = cleaner.remove_duplicate_production_records(
                    start_date=str(start_date),
                    dry_run=True,
                    return_summary=True
                )
                ffm_summary = cleaner.remove_duplicate_facility_measurements(
                    start_date=str(start_date),
                    dry_run=True,
                    return_summary=True
                )

                st.session_state.preview_rows.append(
                    {
                        "company": company,
                        "fm": fm_summary,
                        "lp": lp_summary,
                        "ffm": ffm_summary,
                    }
                )
                progress.progress((idx + 1) / total)

            st.session_state.preview_rows = dedupe_preview_rows(
                st.session_state.preview_rows
            )
            st.success("Preview completed ✔")

    if st.session_state.preview_rows:
        unique_rows = dedupe_preview_rows(st.session_state.preview_rows)
        st.session_state.preview_rows = unique_rows
        st.subheader("Company overview")
        header_cols = st.columns([2, 1, 1, 1, 1])
        header_cols[0].markdown("**Company**")
        header_cols[1].markdown("**Field Measurement Duplicates**")
        header_cols[2].markdown("**Production Duplicates**")
        header_cols[3].markdown("**Facility Measurement Duplicates**")
        header_cols[4].markdown("**Actions**")

        for row in unique_rows:
            company = row["company"]
            fm_count = row["fm"]["delete_count"]
            lp_count = row["lp"]["delete_count"]
            ffm_count = row["ffm"]["delete_count"]

            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            col1.markdown(f"**{company}**")
            col2.markdown(colored_badge(fm_count), unsafe_allow_html=True)
            col3.markdown(colored_badge(lp_count), unsafe_allow_html=True)
            col4.markdown(colored_badge(ffm_count), unsafe_allow_html=True)

            with col5:
                if st.button("⬇ Generate ZIP", key=f"zip-gen-{company}"):
                    with st.spinner("Generating ZIP..."):
                        zip_name, zip_bytes = cleaner.create_combined_backup_zip(
                            company_id=company,
                            start_date=str(start_date),
                            allow_generation=True
                        )
                    if zip_name and zip_bytes:
                        st.session_state.zip_blobs[company] = {
                            "name": zip_name,
                            "data": zip_bytes,
                        }
                        st.success("ZIP ready to download (not saved to disk).")
                    else:
                        st.info("No duplicates found to include in ZIP.")

                if company in st.session_state.zip_blobs:
                    blob = st.session_state.zip_blobs[company]
                    st.download_button(
                        "Download ZIP",
                        blob["data"],
                        file_name=blob["name"],
                        key=f"zip-dl-{company}"
                    )

                if st.button("🗑 Delete data", key=f"delete-{company}"):
                    if dry_run_mode:
                        st.error("Disable dry run mode to delete data.")
                    else:
                        st.warning(f"Deleting data for {company}...")
                        cleaner.company_ids = [company]
                        cleaner.remove_duplicate_measurements(
                            start_date=str(start_date),
                            dry_run=False
                        )
                        cleaner.remove_duplicate_production_records(
                            start_date=str(start_date),
                            dry_run=False
                        )
                        cleaner.remove_duplicate_facility_measurements(
                            start_date=str(start_date),
                            dry_run=False
                        )
                        st.success(f"Deletion completed for {company}")

        st.markdown("—")
        st.caption("ZIP backups are stored as companyname-YYYY-MM-DD.zip in the app folder. Counts refresh when you run preview again.")
