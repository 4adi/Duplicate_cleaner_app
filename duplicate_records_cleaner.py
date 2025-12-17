import json
import zipfile
from io import BytesIO
from pymongo import MongoClient, DeleteMany
from datetime import datetime
from dateutil.relativedelta import relativedelta


class MongoUtils:
    def __init__(self, connection_string: str):
        """
        Initialize MongoDB connection using the provided connection string.
        """
        print("....... MONGO REPOSITORY LOADING  ....... ⌛⌛⌛")
        print("===== MongoUtils =====")

        if not connection_string or not isinstance(connection_string, str):
            raise Exception("❌ Invalid MongoDB connection string.")

        self.__mongo = MongoClient(connection_string)
        self.mongo = self.__mongo

        print("✅ MongoDB connection established.")


class DuplicateCleaner(MongoUtils):

    def __init__(self, connection_string: str):
        super().__init__(connection_string=connection_string)
        self.company_ids = self.fetch_active_company_list()
        print(f"INFO: Active companies fetched: {self.company_ids}")

    def fetch_active_company_list(self): 
        print("START FETCHING REQUIRED COMPANY....")
        data = list(
            self.mongo["ea_management"]["asset_properties"].aggregate([
                {"$match": {"type": "company", "company_id": {"$exists": True}}}
            ])
        )
        return list({item.get("company_id") for item in data if item.get("company_id")})

    # ------------------ Duplicate queries ------------------
    def _field_measurement_duplicates(self, company_id, start_date):
        db = self.mongo[f"{company_id}_Vault"]["live_field_measurements"]
        pipeline = [
            {
                "$addFields": {
                    "converted_prime_iso_date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$dateFromString": {"dateString": "$iso_date"}},
                            "timezone": "America/Chicago"
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "facility_id": "$facility_id",
                        "converted_prime_iso_date": "$converted_prime_iso_date",
                        "oil_rate": {"$ifNull": ["$type_related_info.oil_rate", None]},
                        "water_rate": {"$ifNull": ["$type_related_info.water_rate", None]},
                        "daily_rate": {"$ifNull": ["$type_related_info.daily_rate", None]},
                        "gas_rate": {"$ifNull": ["$type_related_info.gas_rate", None]}
                    },
                    "docs": {"$push": "$_id"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1},
                    "_id.converted_prime_iso_date": {"$gte": start_date}
                }
            }
        ]
        return db, list(db.aggregate(pipeline))

    def _facility_measurement_duplicates(self, company_id, start_date):
        db = self.mongo[f"{company_id}_Vault"]["live_facility_measurements"]
        pipeline = [
            {
                "$match": {
                    "facility_type": "well",
                    "readings.tubing_pressure": {"$exists": True},
                    "readings.casing_pressure": {"$exists": True}
                }
            },
            {
                "$addFields": {
                    "converted_prime_iso_date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$dateFromString": {"dateString": "$iso_date"}},
                            "timezone": "America/Chicago"
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "facility_id": "$facility_id",
                        "converted_prime_iso_date": "$converted_prime_iso_date",
                        "tubing_pressure": {"$ifNull": ["$readings.tubing_pressure", None]},
                        "casing_pressure": {"$ifNull": ["$readings.casing_pressure", None]}
                    },
                    "docs": {"$push": "$_id"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1},
                    "_id.converted_prime_iso_date": {"$gte": start_date}
                }
            }
        ]
        return db, list(db.aggregate(pipeline))

    def _production_duplicates(self, company_id, start_date):
        db = self.mongo[f"{company_id}_Vault"]["live_production"]
        pipeline = [
            {
                "$match": {
                    "record_date": {"$exists": True, "$ne": None, "$type": "number"},
                    "frequency": "daily",
                    "forecast": {"$exists": False},
                    "project_id": {"$exists": False},
                    "ledger_transaction_id": {"$exists": False}
                }
            },
            {
                "$addFields": {
                    "converted_prime_iso_date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": {"$dateFromString": {"dateString": "$iso_date"}},
                            "timezone": "America/Chicago"
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "facility_id": "$facility_id",
                        "converted_prime_iso_date": "$converted_prime_iso_date",
                        "qualifier": "$qualifier",
                        "production_stream": "$production_stream",
                        "volume": "$volume"
                    },
                    "docs": {"$push": "$_id"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1},
                    "_id.converted_prime_iso_date": {"$gte": start_date}
                }
            }
        ]
        return db, list(db.aggregate(pipeline))

    # ----------------------------------------------------------------------
    # REMOVE DUPLICATE MEASUREMENTS WITH RETURN SUMMARY SUPPORT
    # ----------------------------------------------------------------------
    def remove_duplicate_measurements(self, start_date=None, dry_run=True, return_summary=False):
        """
        Removes duplicate field measurement records.
        Returns summary when return_summary=True.
        """

        if start_date is None:
            start_date = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m-%d")

        print(f"\n🚀 Running Duplicate Cleaner...")
        print(f"📅 Start Date: {start_date}")
        print(f"🔧 Dry Run Mode: {dry_run}\n")

        all_company_summaries = []  # Collect summary per company

        for company_id in self.company_ids:

            print(f"INFO : COMPANY: {company_id}")
            db, duplicates = self._field_measurement_duplicates(company_id, start_date)
            print(f"🔍 Found {len(duplicates)} duplicate groups\n")

            bulk_ops = []
            total_deletions = 0

            for group in duplicates:
                doc_ids = group["docs"]
                ids_to_delete = doc_ids[1:]

                if ids_to_delete:
                    bulk_ops.append(DeleteMany({"_id": {"$in": ids_to_delete}}))
                    total_deletions += len(ids_to_delete)

            if dry_run:
                print(f"DRY RUN — Would delete {total_deletions} records.\n")
            else:
                if bulk_ops:
                    result = db.bulk_write(bulk_ops)
                    print(f"🗑 Deleted {result.deleted_count} records.")

            # --- Return summary per company ---
            summary = {
                "company_id": company_id,
                "delete_count": total_deletions,
                "duplicates": duplicates
            }
            all_company_summaries.append(summary)

        if return_summary:
            return all_company_summaries[0] if len(all_company_summaries) == 1 else all_company_summaries  # list of summaries
        
    
    # ----------------------------------------------------------------------
    # REMOVE DUPLICATE FACILITY MEASUREMENTS WITH RETURN SUMMARY SUPPORT
    # ----------------------------------------------------------------------
    def remove_duplicate_facility_measurements(self, start_date=None, dry_run=True, return_summary=False):
        """
        Removes duplicate facility measurement records.
        Returns summary when return_summary=True.
        """

        if start_date is None:
            start_date = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m-%d")

        print(f"\n🚀 Running Duplicate Cleaner...")
        print(f"📅 Start Date: {start_date}")
        print(f"🔧 Dry Run Mode: {dry_run}\n")

        all_company_summaries = []  # Collect summary per company

        for company_id in self.company_ids:

            print(f"INFO : COMPANY: {company_id}")
            db, duplicates = self._facility_measurement_duplicates(company_id, start_date)
            print(f"🔍 Found {len(duplicates)} duplicate groups\n")

            bulk_ops = []
            total_deletions = 0

            for group in duplicates:
                doc_ids = group["docs"]
                ids_to_delete = doc_ids[1:]

                if ids_to_delete:
                    bulk_ops.append(DeleteMany({"_id": {"$in": ids_to_delete}}))
                    total_deletions += len(ids_to_delete)

            if dry_run:
                print(f"DRY RUN — Would delete {total_deletions} records.\n")
            else:
                if bulk_ops:
                    result = db.bulk_write(bulk_ops)
                    print(f"🗑 Deleted {result.deleted_count} records.")

            summary = {
                "company_id": company_id,
                "delete_count": total_deletions,
                "duplicates": duplicates
            }
            all_company_summaries.append(summary)

        if return_summary:
            return all_company_summaries[0] if len(all_company_summaries) == 1 else all_company_summaries  # list of summaries
        

    # ----------------------------------------------------------------------
    # REMOVE DUPLICATE PRODUCTION RECORDS WITH RETURN SUMMARY SUPPORT
    # ----------------------------------------------------------------------
    def remove_duplicate_production_records(self, start_date=None, dry_run=True, return_summary=False):

        if start_date is None:
            start_date = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m-%d")

        print(f"\n🚀 Running Duplicate Cleaner...")
        print(f"📅 Start Date: {start_date}")
        print(f"🔧 Dry Run Mode: {dry_run}\n")

        all_company_summaries = []

        for company_id in self.company_ids:

            print(f"INFO : COMPANY: {company_id}")
            db, duplicates = self._production_duplicates(company_id, start_date)
            print(f"🔍 Found {len(duplicates)} duplicate groups\n")

            bulk_ops = []
            total_deletions = 0

            for group in duplicates:
                doc_ids = group["docs"]
                ids_to_delete = doc_ids[1:]

                if ids_to_delete:
                    bulk_ops.append(DeleteMany({"_id": {"$in": ids_to_delete}}))
                    total_deletions += len(ids_to_delete)

            if dry_run:
                print(f"DRY RUN — Would delete {total_deletions} records.\n")
            else:
                if bulk_ops:
                    result = db.bulk_write(bulk_ops)
                    print(f"🗑 Deleted {result.deleted_count} records.")

            summary = {
                "company_id": company_id,
                "delete_count": total_deletions,
                "duplicates": duplicates
            }
            all_company_summaries.append(summary)

        if return_summary:
            return all_company_summaries[0] if len(all_company_summaries) == 1 else all_company_summaries

    # ----------------------------------------------------------------------
    # CREATE COMBINED ZIP ON DEMAND
    # ----------------------------------------------------------------------
    def create_combined_backup_zip(self, company_id, start_date=None, allow_generation=False):
        """
        Build a single ZIP with duplicate docs for all three collections.
        Only includes a text file per collection when duplicates exist.
        Returns a tuple of (zip_name, bytes) when created, else (None, None).
        """
        if not allow_generation:
            return None, None

        if start_date is None:
            start_date = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m-%d")

        today_str = datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"{company_id}-{today_str}.zip"

        db_fm, fm_duplicates = self._field_measurement_duplicates(company_id, start_date)
        db_lp, lp_duplicates = self._production_duplicates(company_id, start_date)
        db_ffm, ffm_duplicates = self._facility_measurement_duplicates(company_id, start_date)

        added = False
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            def add_docs(db, duplicates, label):
                nonlocal added
                buffer_lines = []
                for group in duplicates:
                    doc_ids = group["docs"]
                    ids_to_delete = doc_ids[1:]
                    if ids_to_delete:
                        for doc_id in ids_to_delete:
                            full_doc = db.find_one({"_id": doc_id})
                            buffer_lines.append(json.dumps(full_doc, default=str))
                if buffer_lines:
                    zip_file.writestr(label, "\n".join(buffer_lines))
                    added = True

            add_docs(db_fm, fm_duplicates, f"{db_fm.database.name}.{db_fm.name}.txt")
            add_docs(db_lp, lp_duplicates, f"{db_lp.database.name}.{db_lp.name}.txt")
            add_docs(db_ffm, ffm_duplicates, f"{db_ffm.database.name}.{db_ffm.name}.txt")

        if not added:
            return None, None

        return zip_filename, buffer.getvalue()
