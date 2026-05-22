import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config.settings import settings

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service to interact with the Google Sheets database."""
    
    def __init__(self) -> None:
        self.spreadsheet_key: str = settings.google_sheets_spreadsheet_key
        self._client: Optional[gspread.Client] = None
        self._worksheet: Optional[gspread.Worksheet] = None

    def _get_client(self) -> gspread.Client:
        """Initializes and returns the gspread client, supporting both explicit service account
        credentials and fallback to Google Application Default Credentials (ADC).
        """
        if self._client is None:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Authenticate via the first valid credentials strategy found:
            # 1. Explicit Service Account JSON string
            # 2. Explicit Service Account file path
            # 3. Google Application Default Credentials (ADC) - handles WIF & local gcloud login
            
            if settings.google_service_account_json:
                try:
                    logger.info("Authenticating with Google via explicit GOOGLE_SERVICE_ACCOUNT_JSON string...")
                    creds_dict = json.loads(settings.google_service_account_json)
                    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                except Exception as e:
                    logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
                    raise
            elif settings.google_service_account_file:
                logger.info(f"Authenticating with Google via explicit GOOGLE_SERVICE_ACCOUNT_FILE: '{settings.google_service_account_file}'...")
                creds = Credentials.from_service_account_file(settings.google_service_account_file, scopes=scopes)
            else:
                import google.auth
                logger.info("No explicit service account keys defined. Authenticating via Google Application Default Credentials (ADC)...")
                try:
                    # Impersonate a service account if configured (ideal for bypassing corporate Workspace OAuth blocks)
                    if settings.google_impersonate_service_account:
                        base_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
                        logger.info(f"Loading base user credentials with cloud-platform scope...")
                        base_creds, project = google.auth.default(scopes=base_scopes)
                        
                        from google.auth import impersonated_credentials
                        logger.info(f"Impersonating Service Account: '{settings.google_impersonate_service_account}' to access Google Sheets/Drive...")
                        creds = impersonated_credentials.Credentials(
                            source_credentials=base_creds,
                            target_principal=settings.google_impersonate_service_account,
                            target_scopes=scopes,
                            lifetime=3600
                        )
                    else:
                        creds, project = google.auth.default(scopes=scopes)
                except Exception as e:
                    logger.exception(f"Failed to load Google Application Default Credentials (ADC): {e}")
                    raise ValueError(
                        "Missing Google Authentication. Please define either 'GOOGLE_SERVICE_ACCOUNT_JSON' (raw string), "
                        "'GOOGLE_SERVICE_ACCOUNT_FILE' (file path), 'GOOGLE_APPLICATION_CREDENTIALS', "
                        "or run 'gcloud auth application-default login' locally."
                    ) from e
            
            self._client = gspread.authorize(creds)
        return self._client

    def _get_worksheet(self) -> gspread.Worksheet:
        """Initializes and returns the target worksheet, ensuring headers exist."""
        if self._worksheet is None:
            client = self._get_client()
            spreadsheet = client.open_by_key(self.spreadsheet_key)
            try:
                self._worksheet = spreadsheet.get_worksheet(0)
            except Exception:
                self._worksheet = spreadsheet.sheet1
            
            # Ensure headers exist
            headers = ["user_id", "display_name", "start_date", "primary_contact", "backup_contact", "updated_at"]
            try:
                row1 = self._worksheet.row_values(1)
                if not row1 or row1 != headers:
                    # Write headers at row 1 if they don't match exactly
                    self._worksheet.insert_row(headers, index=1)
            except Exception as e:
                logger.warning(f"Could not verify headers in worksheet: {e}. Attempting to write.")
                try:
                    self._worksheet.update(values=[headers], range_name="A1:F1")
                except Exception as inner_e:
                    logger.error(f"Failed to write headers: {inner_e}")
        return self._worksheet

    def get_user_record(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a user's record from the sheet by user_id."""
        logger.info(f"Looking up database record for user ID: '{user_id}'")
        try:
            worksheet = self._get_worksheet()
            cell = worksheet.find(user_id, in_column=1)
            if cell is None:
                logger.info(f"No database record found for user ID: '{user_id}'")
                return None
            
            row_num = cell.row
            row_values = worksheet.row_values(row_num)
            
            # Pad row_values to match expected 6 columns
            while len(row_values) < 6:
                row_values.append("")
                
            record = {
                "user_id": row_values[0],
                "display_name": row_values[1],
                "start_date": row_values[2],
                "primary_contact": row_values[3],
                "backup_contact": row_values[4],
                "updated_at": row_values[5]
            }
            logger.info(f"Found database record for user ID: '{user_id}'")
            return record
        except Exception as e:
            logger.exception(f"Failed to retrieve record from Google Sheets for user '{user_id}': {e}")
            raise

    def upsert_user_record(
        self,
        user_id: str,
        display_name: str,
        start_date: str,
        primary_contact: str,
        backup_contact: str
    ) -> None:
        """Inserts or updates a user's record in the sheet."""
        # Never log actual profile fields (PII) to stdout or log files!
        logger.info(f"Upserting database record structure for user ID: '{user_id}'")
        try:
            worksheet = self._get_worksheet()
            cell = worksheet.find(user_id, in_column=1)
            
            updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [user_id, display_name, start_date, primary_contact, backup_contact, updated_at]
            
            if cell is not None:
                row_num = cell.row
                range_label = f"A{row_num}:F{row_num}"
                worksheet.update(values=[row_data], range_name=range_label)
                logger.info(f"Successfully updated database record for user ID: '{user_id}'")
            else:
                worksheet.append_row(row_data)
                logger.info(f"Successfully appended new database record for user ID: '{user_id}'")
        except Exception as e:
            logger.exception(f"Failed to upsert record in Google Sheets for user '{user_id}': {e}")
            raise

# Singleton instance of GoogleSheetsService
google_sheets_service: GoogleSheetsService = GoogleSheetsService()
