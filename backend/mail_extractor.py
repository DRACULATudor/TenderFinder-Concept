import imaplib
import email
import os
import yagmail
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())

user="tlshorts03@gmail.com"
password=os.getenv("GMAIL_PASS")


server = imaplib.IMAP4_SSL("imap.gmail.com", 993)
server.login(user, password)
server.select('inbox')


def pdf_extractor():
    status,mssg = server.search(None,'SUBJECT "TENDER"')
    for single_mail in mssg[0].split():
        status,mssg = server.fetch(single_mail,'(RFC822)')
        if status == 'OK':

            mail = email.message_from_bytes(mssg[0][1])
            for part in mail.walk():
                content_data = part.get_content_type()
                if content_data == "application/pdf":
                    filename = part.get_filename()
                    pdf_content = part.get_payload(decode=True)
                    file_dest = os.path.join("/home/tdoor/PvtProj/TenderFinder/backend", filename)
                    

                    with open(file_dest, "wb") as f:
                        f.write(pdf_content)
                    return True
                else:
                    continue

        else:
            print("No mail found")
            return False