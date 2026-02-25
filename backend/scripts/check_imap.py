import imaplib
import email
from email.header import decode_header

# Assume these are loaded from env or we can hardcode for testing from local
from app.core.config import settings

def check_bounces():
    username = settings.SMTP_USERNAME
    password = settings.SMTP_PASSWORD
    imap_host = "imap.hostinger.com"
    
    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(username, password)
        mail.select("inbox")
        
        # Search for bounced emails
        status, messages = mail.search(None, '(OR (FROM "mailer-daemon") (SUBJECT "Delivery Status Notification"))')
        
        if status == "OK":
            mail_ids = messages[0].split()
            print(f"Found {len(mail_ids)} potential bounce messages.")
            
            # Fetch the latest 3 bounces
            for i in mail_ids[-3:]:
                res, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        origin = msg.get("From")
                        print(f"--- Bounce from: {origin} | Subject: {subject} ---")
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    # Print first 500 chars of bounce reason
                                    print(body[:500])
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                            print(body[:500])
                        print("-" * 50)
        else:
            print("No bounce messages found.")
            
        mail.logout()
    except Exception as e:
        print(f"IMAP Error: {e}")

if __name__ == "__main__":
    check_bounces()
