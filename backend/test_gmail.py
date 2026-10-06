from app.gmail_service import search_emails, read_email


# Step 1: Find one email
emails = search_emails(
    query="from:google",
    max_results=1
)

print("\nFound email:")
print(emails)


# Step 2: Read that email
if emails:

    message_id = emails[0]["id"]

    email = read_email(
        message_id
    )

    print("\nFull email:")
    print(email)

else:

    print("No emails found.")