
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3, hashlib
from datetime import datetime
from io import BytesIO
from pathlib import Path

app = Flask(__name__)
app.secret_key = "legalease-college-demo"
DB = Path(__file__).with_name("legalease.db")

TYPES = {
    "rental": "Rental Agreement",
    "nda": "Non-Disclosure Agreement",
    "employment": "Employment Agreement",
    "complaint": "Legal Complaint Letter",
    "sale": "Sale Agreement",
    "authorization": "Authorization Letter"
}

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c=conn()
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY, user_id INTEGER, type TEXT, title TEXT, content TEXT, created_at TEXT)""")
    c.commit(); c.close()

def pw(s): return hashlib.sha256(s.encode()).hexdigest()

def make_doc(t,d):
    A=d.get("party_a","").strip() or "[Party A]"
    B=d.get("party_b","").strip() or "[Party B]"
    S=d.get("subject","").strip() or "[Subject / Purpose]"
    amt=d.get("amount","").strip() or "[Amount]"
    dur=d.get("duration","").strip() or "[Duration]"
    date=d.get("date","").strip() or datetime.now().strftime("%d-%m-%Y")
    juris=d.get("jurisdiction","").strip() or "India"
    details=d.get("details","").strip() or "[Additional details to be added]"
    common=f"\n\nJurisdiction: {juris}\nDate: {date}\n\n"
    if t=="rental":
        title="RENTAL AGREEMENT"
        body=f"""LANDLORD: {A}
TENANT: {B}

1. PROPERTY AND PURPOSE
The landlord agrees to rent the property for lawful use as agreed by the parties.

2. RENT
Monthly rent / consideration: {amt}.

3. TERM
Rental period: {dur}.

4. TERMS
The parties shall specify deposit, maintenance, notice, renewal and other applicable conditions.

5. ADDITIONAL DETAILS
{details}

SIGNATURES
Landlord: __________________
Tenant: ____________________"""
    elif t=="nda":
        title="NON-DISCLOSURE AGREEMENT"
        body=f"""DISCLOSING PARTY: {A}
RECEIVING PARTY: {B}
PURPOSE: {S}

1. CONFIDENTIAL INFORMATION
Non-public business, technical, financial, customer and project information may be treated as confidential.

2. OBLIGATIONS
The receiving party shall use confidential information only for the agreed purpose and take reasonable steps to prevent unauthorized disclosure.

3. TERM
Confidentiality period: {dur}.

4. ADDITIONAL TERMS
{details}

SIGNATURES
Disclosing Party: __________
Receiving Party: ____________"""
    elif t=="employment":
        title="EMPLOYMENT AGREEMENT"
        body=f"""EMPLOYER: {A}
EMPLOYEE: {B}
ROLE: {S}

1. COMPENSATION
Compensation: {amt}.

2. TERM
Employment / probation period: {dur}.

3. DUTIES
The employee shall perform the duties assigned for the role and follow lawful workplace policies.

4. CONFIDENTIALITY
The parties should define confidentiality and intellectual-property obligations.

5. ADDITIONAL DETAILS
{details}

SIGNATURES
Employer: __________________
Employee: __________________"""
    elif t=="complaint":
        title="LEGAL COMPLAINT LETTER"
        body=f"""FROM: {A}
TO: {B}
SUBJECT: {S}

Dear Sir/Madam,

I am writing to formally record the following concern and request an appropriate response.

FACTS AND DETAILS:
{details}

REQUESTED ACTION:
Please review the matter and provide an appropriate response or resolution within a reasonable period.

Sincerely,
{A}"""
    elif t=="sale":
        title="SALE AGREEMENT"
        body=f"""SELLER: {A}
BUYER: {B}
SUBJECT / PROPERTY: {S}
SALE CONSIDERATION: {amt}

1. SALE
The seller agrees to sell and the buyer agrees to purchase the subject described by the parties, subject to the final legally reviewed terms.

2. PAYMENT
Payment terms: {details}

3. COMPLETION
Expected completion / possession period: {dur}.

4. OTHER TERMS
The parties should add title, delivery, taxes, warranties and dispute provisions applicable to the transaction.

SIGNATURES
Seller: ____________________
Buyer: _____________________"""
    else:
        title="AUTHORIZATION LETTER"
        body=f"""AUTHORIZING PERSON: {A}
AUTHORIZED PERSON: {B}
PURPOSE: {S}

I hereby authorize the above-named person to act on my behalf for the stated purpose, subject to the limits described below.

SCOPE / DETAILS:
{details}

VALIDITY:
{dur}

SIGNATURE
Authorizing Person: __________________
Date: {date}"""
    disclaimer="\n\n---\nEDUCATIONAL DRAFT — NOT LEGAL ADVICE. Have a qualified legal professional review this document before signing, submitting or relying on it."
    return title, title+common+body+disclaimer

@app.route("/")
def home():
    if "uid" not in session: return redirect(url_for("login"))
    c=conn()
    docs=c.execute("SELECT * FROM documents WHERE user_id=? ORDER BY id DESC",(session["uid"],)).fetchall()
    c.close()
    return render_template("dashboard.html", types=TYPES, docs=docs, name=session.get("name"))

@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower(); password=request.form["password"]
        try:
            c=conn(); c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",(name,email,pw(password))); c.commit(); c.close()
            flash("Account created. Please login."); return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
    return render_template("auth.html", signup=True)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower(); password=request.form["password"]
        c=conn(); u=c.execute("SELECT * FROM users WHERE email=? AND password=?",(email,pw(password))).fetchone(); c.close()
        if u:
            session["uid"]=u["id"]; session["name"]=u["name"]; return redirect(url_for("home"))
        flash("Invalid email or password.")
    return render_template("auth.html", signup=False)

@app.get("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

@app.post("/generate")
def generate():
    if "uid" not in session: return redirect(url_for("login"))
    t=request.form["document_type"]; title,content=make_doc(t,request.form)
    c=conn(); cur=c.execute("INSERT INTO documents(user_id,type,title,content,created_at) VALUES(?,?,?,?,?)",
        (session["uid"],t,title,content,datetime.now().strftime("%d-%m-%Y %H:%M")))
    did=cur.lastrowid; c.commit(); c.close()
    return render_template("result.html",title=title,content=content,did=did)

@app.get("/download/<int:did>")
def download(did):
    if "uid" not in session: return redirect(url_for("login"))
    c=conn(); row=c.execute("SELECT * FROM documents WHERE id=? AND user_id=?",(did,session["uid"])).fetchone(); c.close()
    if not row: return "Not found",404
    return send_file(BytesIO(row["content"].encode()),as_attachment=True,
                     download_name=f"LegalEase_{did}.txt",mimetype="text/plain")

@app.get("/delete/<int:did>")
def delete(did):
    if "uid" in session:
        c=conn(); c.execute("DELETE FROM documents WHERE id=? AND user_id=?",(did,session["uid"])); c.commit(); c.close()
    return redirect(url_for("home"))

if __name__=="__main__":
    init_db()
    app.run(debug=True)
