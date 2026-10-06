from app.gmail_service import search_emails


results = search_emails(
    "in:inbox",
    max_results=5
)

print("\nGmail Search Results:\n")

for email in results:

    print("ID:", email.get("id"))
    print("From:", email.get("from"))
    print("Subject:", email.get("subject"))
    print("Date:", email.get("date"))
    print("-" * 50)

