import csv
import io
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.leads import ImportBatch, ImportRow, Company, Contact
from app.services.normalization import (
    normalize_domain,
    normalize_email,
    split_full_name,
    is_consumer_webmail_domain,
)
from app.services.suppression import check_is_suppressed
from app.services.deduplication import find_existing_company, find_existing_contact

FIELD_ALIASES = {
    "company_name": [
        "company", "company_name", "company name", "organization", "account",
        "account_name", "account name", "business", "business_name", "business name",
        "firm", "employer"
    ],
    "domain": [
        "domain", "website", "company_website", "company website", "company_domain",
        "company domain", "url", "web", "web_site", "website_url", "web_url", "web url",
        "site", "site_url", "site url", "domain_name", "domain name", "company_url", "company url"
    ],
    "email": [
        "email", "work_email", "work email", "contact_email", "contact email",
        "email_address", "email address", "mail", "business_email", "e-mail"
    ],
    "first_name": [
        "first_name", "first name", "first", "given_name", "given name", "fname"
    ],
    "last_name": [
        "last_name", "last name", "last", "surname", "family_name", "family name", "lname"
    ],
    "full_name": [
        "full_name", "full name", "name", "contact_name", "contact name", "lead_name", "lead name"
    ],
    "title": [
        "title", "job_title", "job title", "role", "position", "occupation", "job"
    ],
    "phone": [
        "phone", "phone_number", "phone number", "telephone", "mobile", "direct_phone",
        "work_phone", "cell"
    ],
    "linkedin_url": [
        "linkedin", "linkedin_url", "linkedin url", "linkedin_profile", "linkedin profile",
        "person_linkedin_url", "contact_linkedin"
    ],
    "industry": [
        "industry", "sector", "vertical", "business_vertical"
    ],
    "employee_count_range": [
        "employees", "employee_count", "employee count", "headcount", "company_size",
        "company size", "size", "number_of_employees"
    ],
    "city": ["city", "metro", "town"],
    "state": ["state", "province", "region"],
    "country": ["country", "nation"],
}


def decode_file_bytes(content: bytes) -> str:
    """Decodes file bytes attempting standard encodings."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def detect_delimiter(text_sample: str) -> str:
    """Detects delimiter from text sample, defaulting to comma."""
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text_sample[:4096])
        if dialect.delimiter in (",", ";", "\t", "|"):
            return dialect.delimiter
    except Exception:
        pass

    # Heuristic count in first non-empty line
    lines = [line for line in text_sample.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        counts = {
            ",": first_line.count(","),
            ";": first_line.count(";"),
            "\t": first_line.count("\t"),
            "|": first_line.count("|"),
        }
        best = max(counts, key=counts.get)
        if counts[best] > 0:
            return best
    return ","


def clean_header_key(h: str) -> str:
    """Normalizes header string for alias matching."""
    return re.sub(r"[^a-z0-9]", "", h.strip().lower())


def auto_map_headers(headers: List[str]) -> Dict[str, str]:
    """
    Suggests canonical field mappings based on header name aliases.
    Returns: {canonical_field: raw_header_name}
    """
    cleaned_to_raw = {clean_header_key(h): h for h in headers if h.strip()}
    mapping = {}

    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            cleaned_alias = clean_header_key(alias)
            if cleaned_alias in cleaned_to_raw:
                mapping[canonical] = cleaned_to_raw[cleaned_alias]
                break

    return mapping


def detect_columns_and_preview(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parses the initial rows of an uploaded lead file, detects delimiters,
    extracts sample rows, and returns suggested column mappings.
    """
    text_content = decode_file_bytes(file_content)
    delimiter = detect_delimiter(text_content)

    reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
    headers = []
    try:
        headers = next(reader)
        headers = [h.strip() for h in headers if h is not None]
    except StopIteration:
        headers = []

    suggested_mappings = auto_map_headers(headers)

    sample_rows = []
    for _ in range(5):
        try:
            row = next(reader)
            row_dict = {}
            for i, h in enumerate(headers):
                if i < len(row):
                    row_dict[h] = row[i].strip()
                else:
                    row_dict[h] = ""
            sample_rows.append(row_dict)
        except StopIteration:
            break

    # Count approximate total lines
    total_lines = max(0, len([l for l in text_content.splitlines() if l.strip()]) - 1)

    return {
        "filename": filename,
        "delimiter": delimiter,
        "headers": headers,
        "suggested_mappings": suggested_mappings,
        "sample_rows": sample_rows,
        "total_estimated_rows": total_lines,
    }


async def execute_lead_import(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    filename: str,
    file_content: bytes,
    column_mapping: Dict[str, str],
) -> Dict[str, Any]:
    """
    Executes streaming lead ingestion:
    - Normalizes domains and emails.
    - Enforces workspace suppression list.
    - Performs deterministic deduplication against existing companies and contacts.
    - Records row-level quarantine and audit data.
    - Updates batch summary counters.
    """
    text_content = decode_file_bytes(file_content)
    delimiter = detect_delimiter(text_content)

    # Invert mapping: {raw_header: canonical_field}
    header_to_field = {v: k for k, v in column_mapping.items() if v}

    reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
    try:
        headers = next(reader)
        headers = [h.strip() for h in headers]
    except StopIteration:
        headers = []

    batch = ImportBatch(
        workspace_id=workspace_id,
        filename=filename,
        total_rows=0,
        valid_rows=0,
        duplicate_rows=0,
        suppressed_rows=0,
        error_rows=0,
        status="PROCESSING",
    )
    db.add(batch)
    await db.flush()

    total_rows = 0
    valid_count = 0
    duplicate_count = 0
    suppressed_count = 0
    error_count = 0

    row_num = 0
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue

        row_num += 1
        total_rows += 1

        # Extract mapped values
        raw_dict = {}
        row_fields = {}
        for idx, h in enumerate(headers):
            val = row[idx].strip() if idx < len(row) else ""
            raw_dict[h] = val
            if h in header_to_field:
                row_fields[header_to_field[h]] = val

        # Handle names
        first_name = row_fields.get("first_name", "").strip()
        last_name = row_fields.get("last_name", "").strip()
        if not first_name and not last_name and row_fields.get("full_name"):
            first_name, last_name = split_full_name(row_fields.get("full_name"))

        # Extract and normalize identifiers
        raw_company = row_fields.get("company_name", "").strip()
        raw_domain = row_fields.get("domain", "").strip()
        raw_email = row_fields.get("email", "").strip()

        normalized_email = normalize_email(raw_email)
        normalized_dom = normalize_domain(raw_domain)
        # Fallback domain from email ONLY for corporate business domains (excluding consumer webmail)
        if not normalized_dom and normalized_email:
            email_domain = normalize_domain(normalized_email)
            if email_domain and not is_consumer_webmail_domain(email_domain):
                normalized_dom = email_domain

        # Validation: Must have at least a normalized corporate domain or a valid contact email
        if not normalized_dom and not normalized_email:
            error_count += 1
            import_row = ImportRow(
                workspace_id=workspace_id,
                batch_id=batch.id,
                row_number=row_num,
                raw_data=raw_dict,
                status="ERROR",
                error_details={"reason": "Missing required domain or email identifier"},
            )
            db.add(import_row)
            continue

        # Check Suppression
        is_suppressed, suppression_reason = await check_is_suppressed(
            db,
            workspace_id=workspace_id,
            normalized_domain=normalized_dom,
            normalized_email=normalized_email,
        )
        if is_suppressed:
            suppressed_count += 1
            import_row = ImportRow(
                workspace_id=workspace_id,
                batch_id=batch.id,
                row_number=row_num,
                raw_data=raw_dict,
                status="SUPPRESSED",
                error_details={"reason": suppression_reason},
            )
            db.add(import_row)
            continue

        # Check Deduplication
        existing_company = None
        if normalized_dom:
            existing_company = await find_existing_company(db, workspace_id, normalized_dom)

        existing_contact = None
        if normalized_email:
            existing_contact = await find_existing_contact(db, workspace_id, normalized_email)

        # If both entities exist or solitary entity exists, mark DUPLICATE
        is_duplicate = False
        if normalized_dom and normalized_email:
            if existing_company and existing_contact:
                is_duplicate = True
        elif normalized_dom and not normalized_email:
            if existing_company:
                is_duplicate = True
        elif normalized_email and not normalized_dom:
            if existing_contact:
                is_duplicate = True

        if is_duplicate:
            duplicate_count += 1
            import_row = ImportRow(
                workspace_id=workspace_id,
                batch_id=batch.id,
                row_number=row_num,
                raw_data=raw_dict,
                status="DUPLICATE",
                error_details={"reason": "Account or Contact already exists in workspace"},
            )
            db.add(import_row)
            continue

        # Valid row -> Create Company if a verified corporate domain is available
        company = existing_company
        if not company and normalized_dom:
            company_display_name = raw_company or (normalized_dom.split(".")[0].title() if normalized_dom else "Unnamed Company")
            company = Company(
                workspace_id=workspace_id,
                name=company_display_name,
                domain=raw_domain or normalized_dom,
                normalized_domain=normalized_dom,
                industry=row_fields.get("industry") or None,
                employee_count_range=row_fields.get("employee_count_range") or None,
                city=row_fields.get("city") or None,
                state=row_fields.get("state") or None,
                country=row_fields.get("country") or None,
                status="ACTIVE",
                custom_attributes={k: v for k, v in raw_dict.items() if k not in header_to_field},
            )
            db.add(company)
            await db.flush()

        if normalized_email and not existing_contact:
            contact = Contact(
                workspace_id=workspace_id,
                company_id=company.id if company else None,
                email=normalized_email,
                first_name=first_name or None,
                last_name=last_name or None,
                title=row_fields.get("title") or None,
                phone=row_fields.get("phone") or None,
                linkedin_url=row_fields.get("linkedin_url") or None,
                status="ACTIVE",
                custom_attributes={k: v for k, v in raw_dict.items() if k not in header_to_field},
            )
            db.add(contact)
            await db.flush()

        valid_count += 1
        import_row = ImportRow(
            workspace_id=workspace_id,
            batch_id=batch.id,
            row_number=row_num,
            raw_data=raw_dict,
            status="VALID",
            error_details=None,
        )
        db.add(import_row)

    # Finalize batch
    batch.total_rows = total_rows
    batch.valid_rows = valid_count
    batch.duplicate_rows = duplicate_count
    batch.suppressed_rows = suppressed_count
    batch.error_rows = error_count
    batch.status = "COMPLETED"

    await db.flush()

    return {
        "batch_id": str(batch.id),
        "filename": filename,
        "total_rows": total_rows,
        "valid_rows": valid_count,
        "duplicate_rows": duplicate_count,
        "suppressed_rows": suppressed_count,
        "error_rows": error_count,
        "status": "COMPLETED",
    }
