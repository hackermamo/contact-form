from flask import Flask, request, render_template
import requests
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Google Form URLs
FORM_VIEW_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdoAIYzgpfAHvFhwOAfgxDwJSfjAQanC4_4wjG6Dnd4Dq8d2A/viewform"
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdoAIYzgpfAHvFhwOAfgxDwJSfjAQanC4_4wjG6Dnd4Dq8d2A/formResponse"

@app.route("/")
def index():
    # Render the custom form. `success` and `message` are used to show feedback after submit.
    return render_template("form.html", success=False, message=None)

@app.route("/submit", methods=["POST"])
def submit():
    # Map your custom form fields to Google Form entry IDs (extracted from the provided form HTML)
    data = {
        "entry.2005620554": request.form.get("name", ""),    # Name
        "entry.1045781291": request.form.get("email", ""),   # Email
        "entry.1065046570": request.form.get("address", ""), # Address (textarea)
        "entry.1166974658": request.form.get("phone", "")    # Phone number
    }

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Referer": FORM_VIEW_URL,
    }

    # Try to GET the viewform page to pick up any hidden fields (fbzx, token, fvv, pageHistory, etc.)
    try:
        r = session.get(FORM_VIEW_URL, headers={"User-Agent": headers["User-Agent"]}, timeout=10)
        r.raise_for_status()
        html = r.text

        # Common hidden field names we may need
        for name in ("fbzx", "token", "fvv", "pageHistory", "partialResponse", "tag", "submissionTimestamp"):
            m = re.search(r'name="%s"\s+value="([^"]*)"' % re.escape(name), html)
            if m:
                data[name] = m.group(1)
                logging.info("Found hidden field %s=%s", name, m.group(1))
    except requests.RequestException as e:
        logging.warning("Could not fetch viewform page: %s", e)
        # Continue without hidden fields; may still work if form is public

    try:
        resp = session.post(GOOGLE_FORM_URL, data=data, headers=headers, timeout=10)
        status = resp.status_code
        body_snippet = resp.text[:800].replace('\n', ' ')
        logging.info("Google formResponse POST status=%s", status)
        logging.debug("Response body snippet: %s", body_snippet)

        if 200 <= status < 300:
            message = "Thanks — your response was submitted."
        elif status == 401:
            # Common cause: form restricted to signed-in users / domain
            message = ("Submission returned 401 (Unauthorized). "
                       "Check the Google Form settings: make sure it is open to 'Anyone with the link' and does NOT "
                       "require sign-in or restrict to a G Suite/Google Workspace domain.")
        else:
            message = f"Submitted but received status {status}. Response preview: {body_snippet}"
    except requests.RequestException as e:
        logging.exception("RequestException when posting to Google Form: %s", e)
        message = f"There was an error submitting your response: {e}"

    # Re-render the custom form with a success/failure message (no redirect to Google Forms)
    return render_template("form.html", success=True, message=message)

if __name__ == "__main__":
    app.run(debug=True)
