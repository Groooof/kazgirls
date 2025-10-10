from enum import StrEnum

from schemas.bases import SchemeBase


class MimeType(StrEnum):
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    csv = "text/csv"
    ods = "application/vnd.oasis.opendocument.spreadsheet"
    docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    pdf = "application/pdf"
    mp3 = "audio/mpeg"
    wav = "audio/mpeg"
    ogg = "audio/ogg"

    @classmethod
    def spreadsheet(cls):
        return cls.xlsx, cls.csv, cls.ods

    @classmethod
    def audio(cls):
        return cls.mp3, cls.wav, cls.ogg

    @classmethod
    def custom_files(cls):
        return cls.xlsx, cls.csv, cls.ods, cls.docx, cls.pdf


class RawFile(SchemeBase):
    filename: str
    mime_type: MimeType


class RawFileInMemory(RawFile):
    content: bytes | str
