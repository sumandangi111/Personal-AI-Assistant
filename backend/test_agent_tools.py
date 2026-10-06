from app.agent_tools import gmail_search_tool


result = gmail_search_tool(
    query="in:inbox",
    max_results=3
)

print("\nGmail Tool Result:\n")

for email in result["results"]:
    print("From:", email.get("from"))
    print("Subject:", email.get("subject"))
    print("Date:", email.get("date"))
    print("-" * 50)

