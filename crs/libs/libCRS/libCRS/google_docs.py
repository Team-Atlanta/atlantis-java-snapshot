import os
import gspread
from google.oauth2.service_account import Credentials

from .util import get_env


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheet:
    def __init__(self, cred_file, sheet_url):
        credentials = Credentials.from_service_account_file(cred_file, scopes=SCOPES)
        self.client = gspread.authorize(credentials)
        self.sheet = self.client.open_by_url(sheet_url)
        self.worksheet = None

    def set_worksheet(self, title):
        try:
            self.worksheet = self.sheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            self.worksheet = self.sheet.add_worksheet(title=title, rows=100, cols=100)

    def next_row_idx(self):
        return len(self.worksheet.col_values(1)) + 2

    def add_rows(self, rows, header):
        idx = self.next_row_idx()
        range_name = f"A{idx}"
        self.worksheet.update(range_name=range_name, values=[header] + rows)


def update_sheet(rows, header, prefix=""):
    url = get_env("SHEET_URL")
    if url is None:
        return
    cp = get_env("TARGET")
    crs = get_env("TARGET_CRS")
    worksheet = f"{crs}-{cp}"
    if prefix:
        worksheet = prefix + worksheet
    commit = get_env("COMMIT")
    cred_file = get_env("DOCS_CRED_PATH")
    sheet = GoogleSheet(cred_file, url)
    sheet.set_worksheet(worksheet)
    rows = list(map(lambda r: [commit] + r, rows))
    header = ["COMMIT"] + header + [commit]
    sheet.add_rows(rows, header)
