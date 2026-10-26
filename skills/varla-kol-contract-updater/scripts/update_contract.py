from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from docx import Document


def set_paragraph_text(paragraph, text: str) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def remove_paragraph(paragraph) -> None:
    """Remove a body paragraph while retaining all surrounding DOCX structure."""
    element = paragraph._element
    element.getparent().remove(element)


def all_paragraphs(document):
    yield from document.paragraphs
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
    for section in document.sections:
        yield from section.header.paragraphs
        yield from section.footer.paragraphs
        for table in section.header.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.paragraphs
        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.paragraphs


def value_after_label(text: str, label: str) -> str:
    return text[len(label):].strip() if text.startswith(label) else ""


def collect_old_values(document) -> set[str]:
    values: set[str] = set()
    labels = (
        "Full Name:",
        "Shipping Address:",
        "Phone Number:",
        "Code Name:",
        "Signature of the Influencer:",
    )
    for paragraph in all_paragraphs(document):
        text = paragraph.text.strip()
        for label in labels:
            value = value_after_label(text, label)
            if value:
                values.add(value)
        if text.startswith("This contract is made between the influencer "):
            match = re.search(
                r"between the influencer (.+?) and Varla / the advertiser", text
            )
            if match:
                values.add(match.group(1).strip())
    for table in document.tables:
        for row in table.rows:
            if len(row.cells) < 2:
                continue
            label = row.cells[0].text.strip()
            if label == "Bike / Product Model":
                value = row.cells[1].text.strip()
                if value:
                    values.add(value)
            if label in {"Collaborating Creator", "Signing Party / Influencer"}:
                text = row.cells[1].text.strip()
                values.update(
                    re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
                )
                values.update(
                    re.findall(r"(?<![\w.+-])@[A-Za-z0-9_.]+", text)
                )
    return {value for value in values if len(value) >= 4}


def xml_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
            if name.endswith(".xml")
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--name")
    parser.add_argument("--email")
    parser.add_argument("--rate")
    parser.add_argument("--date")
    parser.add_argument("--bike-model")
    parser.add_argument("--color")
    parser.add_argument("--accessory-note")
    parser.add_argument(
        "--model-only",
        action="store_true",
        help="Update only product-model text, table row, and model hashtag.",
    )
    parser.add_argument("--handle")
    parser.add_argument("--shipping-address")
    parser.add_argument("--phone")
    parser.add_argument("--discount-code")
    parser.add_argument("--signature-name")
    args = parser.parse_args()

    if not args.model_only:
        required_args = {
            "--name": args.name,
            "--email": args.email,
            "--rate": args.rate,
            "--date": args.date,
        }
        missing_args = [flag for flag, value in required_args.items() if not value]
        if missing_args:
            parser.error(f"required unless --model-only is used: {', '.join(missing_args)}")

    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    if source == output:
        raise SystemExit("Refusing to overwrite the source document.")

    document = Document(source)
    old_values = collect_old_values(document)
    before_shape = {
        "paragraphs": len(document.paragraphs),
        "tables": len(document.tables),
        "table_shapes": [
            [len(row.cells) for row in table.rows] for table in document.tables
        ],
    }

    # Impact IDs are no longer part of Varla creator agreements.  Remove the
    # complete legacy line instead of replacing it with a placeholder.
    impact_lines = [
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.strip().startswith("Impact ID Number:")
    ]
    for paragraph in impact_lines:
        remove_paragraph(paragraph)

    creator_id = args.handle or args.name
    unknown = "To be confirmed"
    bike_model = args.bike_model or unknown
    display_bike_model = (
        f"{bike_model} ({args.color.strip()})"
        if args.color and args.color.strip() and bike_model != unknown
        else bike_model
    )
    replacements = {
        "Full Name:": args.name,
        "Shipping Address:": args.shipping_address or unknown,
        "Phone Number:": args.phone or unknown,
        "Code Name:": (
            f"{args.discount_code or unknown}     {args.rate} (Valid for 2 months)"
        ),
        "Signature of the Influencer:": args.signature_name or "",
        "Date:": args.date,
    }

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text.startswith("This contract is made between the influencer "):
            set_paragraph_text(
                paragraph,
                f"This contract is made between the influencer {creator_id} and "
                "Varla / the advertiser. Both parties acknowledge the terms of "
                "this contract and agree to comply.",
            )
            continue
        if text.startswith("The influencer will receive 1 Varla electric dirt bike."):
            accessory_note = (
                f" {args.accessory_note.strip()}"
                if args.accessory_note and args.accessory_note.strip()
                else ""
            )
            set_paragraph_text(
                paragraph,
                f"The influencer will receive 1 {display_bike_model}. "
                "The final model must match the model confirmed by Varla before shipment."
                f"{accessory_note}",
            )
            continue
        if text.startswith("Use relevant hashtags such as "):
            if args.bike_model:
                model_tag = re.sub(r"[^A-Za-z0-9]", "", args.bike_model)
                hashtags = (
                    f"#Varla #{model_tag} #ElectricDirtBike #OffRoad "
                    "#Ebike #DirtBike."
                )
            else:
                hashtags = "#Varla #ElectricDirtBike #OffRoad #Ebike #DirtBike."
            set_paragraph_text(
                paragraph, f"Use relevant hashtags such as {hashtags}"
            )
            continue
        if text.startswith("Exclusive $100 Discount Code for Your Audience"):
            # A discount code is assigned separately; never retain an old
            # creator's code inside a newly prepared agreement.
            set_paragraph_text(
                paragraph, "Exclusive $100 Discount Code for Your Audience"
            )
            continue
        if args.model_only:
            continue
        for label, value in replacements.items():
            if text.startswith(label):
                set_paragraph_text(
                    paragraph, f"{label} {value}" if value else label
                )
                break

    for table in document.tables:
        for row in table.rows:
            if len(row.cells) < 2:
                continue
            label = row.cells[0].text.strip()
            if label == "Bike / Product Model":
                set_paragraph_text(
                    row.cells[1].paragraphs[0],
                    f"1 {display_bike_model}. Final model confirmed by Varla before shipment.",
                )
            elif label == "Collaborating Creator" and not args.model_only:
                set_paragraph_text(row.cells[1].paragraphs[0], creator_id)
            elif label == "Signing Party / Influencer" and not args.model_only:
                set_paragraph_text(
                    row.cells[1].paragraphs[0], f"{args.name} / {args.email}"
                )

    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)

    checked = Document(output)
    after_shape = {
        "paragraphs": len(checked.paragraphs),
        "tables": len(checked.tables),
        "table_shapes": [
            [len(row.cells) for row in table.rows] for table in checked.tables
        ],
    }
    expected_shape = dict(before_shape)
    expected_shape["paragraphs"] -= len(impact_lines)
    if expected_shape != after_shape:
        raise SystemExit("Document structure changed unexpectedly.")

    packed_text = xml_text(output)
    required = (
        [display_bike_model]
        if args.model_only
        else [args.name, args.email, args.rate, args.date, display_bike_model]
    )
    missing = [value for value in required if value not in packed_text]
    retained = sorted(value for value in old_values if value in packed_text)
    legacy_fields = []
    if "Impact ID Number:" in packed_text:
        legacy_fields.append("Impact ID Number")
    if "ananda100" in packed_text.lower():
        legacy_fields.append("ananda100")
    if missing or retained or legacy_fields:
        raise SystemExit(
            json.dumps(
                {
                    "missing_required": missing,
                    "retained_old_values": retained,
                    "legacy_fields": legacy_fields,
                },
                ensure_ascii=False,
            )
        )

    print(
        json.dumps(
            {
                "output": str(output),
                "required_values_present": required,
                "bike_model": bike_model,
                "old_personal_values_removed": sorted(old_values),
                "structure_unchanged_except_removed_impact_lines": len(impact_lines),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
