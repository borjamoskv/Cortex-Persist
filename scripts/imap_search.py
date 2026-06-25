import imaplib
import email
from email.header import decode_header
import sys

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("borjabilbo84@gmail.com", "egqi qgti hpek uhdg")
mail.select("inbox")

status, messages = mail.search(None, 'BODY "github_pat_"')
if status == "OK" and messages[0]:
    for num in messages[0].split():
        res, msg = mail.fetch(num, "(RFC822)")
        for response_part in msg:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                print("Subject:", msg["subject"])
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            print(part.get_payload(decode=True).decode('utf-8', 'ignore'))
                else:
                    print(msg.get_payload(decode=True).decode('utf-8', 'ignore'))

status, messages = mail.search(None, 'BODY "ghp_"')
if status == "OK" and messages[0]:
    for num in messages[0].split():
        res, msg = mail.fetch(num, "(RFC822)")
        for response_part in msg:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                print("Subject:", msg["subject"])
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            print(part.get_payload(decode=True).decode('utf-8', 'ignore'))
                else:
                    print(msg.get_payload(decode=True).decode('utf-8', 'ignore'))
