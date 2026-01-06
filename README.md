# PDA Question Website (Static GitHub Pages)

Repository name: **pdaquestion.github.io**  
Hosting URL (default): **https://pdaquestion.github.io**  
Custom domain (later): **PDAQuestion.com**

This is a static HTML/CSS/JavaScript site designed for GitHub Pages.
- Mobile-first, responsive
- Crisis-friendly UI (large buttons, calm colors, minimal cognitive load)
- WCAG 2.1 AA-minded structure (semantic headings, skip link, keyboard-friendly nav)
- No external dependencies (no frameworks, no CDNs)

## Folder Structure

```
pdaquestion.github.io/
  index.html
  what-is-pda.html
  features.html
  for-parents.html
  for-professionals.html
  resources.html
  about.html
  download.html
  assets/
    css/
      styles.css
    js/
      main.js
    img/
      favicon.svg
      icons/
        emergency.svg
        chat.svg
        brain.svg
        metaphor.svg
        siblings.svg
        tracking.svg
```

## Quick Start (Local Preview)

You can open `index.html` directly in a browser, or run a tiny local server:

### Option A (Python)
```bash
python -m http.server 8000
```
Then open: `http://localhost:8000`

### Option B (VS Code)
Use the "Live Server" extension (optional).

## Deploy to GitHub Pages

### 1) Create the repository
1. Log into GitHub with your `pdaquestion` account.
2. Create a new repository named **pdaquestion.github.io** (this exact name matters for user pages).
3. Keep it Public (recommended for GitHub Pages).

### 2) Upload the files
**Option A: Upload in the browser**
1. Open the repo on GitHub.
2. Click **Add file** → **Upload files**
3. Drag and drop the site files and folders (everything in this zip).
4. Commit to the `main` branch.

**Option B: Git via terminal**
```bash
git clone https://github.com/pdaquestion/pdaquestion.github.io.git
cd pdaquestion.github.io
# copy the site files into this folder
git add .
git commit -m "Initial site"
git push origin main
```

### 3) Enable GitHub Pages
1. In the repo, go to **Settings** → **Pages**
2. Under **Build and deployment**
   - Source: **Deploy from a branch**
   - Branch: **main** / **(root)**
3. Save
4. Wait for GitHub to publish the site
5. Visit: https://pdaquestion.github.io

## Connect GoDaddy Domain (PDAQuestion.com)

You can connect the custom domain after GitHub Pages is working.

### Step 1: Add domain in GitHub
1. Repo → **Settings** → **Pages**
2. Under **Custom domain**, enter: `pdaquestion.com`
3. Save
4. Enable **Enforce HTTPS** after DNS is correct (it may take a little time)

### Step 2: DNS records in GoDaddy
Log in to GoDaddy → your domain → **DNS**:

#### A Records (root domain)
Set these four A records for **@**:
- `185.199.108.153`
- `185.199.109.153`
- `185.199.110.153`
- `185.199.111.153`

#### CNAME (www)
Add a CNAME record:
- Host: `www`
- Points to: `pdaquestion.github.io`

### Step 3: Verify
DNS can take time to propagate. Once GitHub verifies, your site will load at:
- https://pdaquestion.com
- https://www.pdaquestion.com

## Amazon Affiliate Notes

On `resources.html`, each button uses this placeholder format:

`https://www.amazon.com/dp/[BOOK-ASIN-X]?tag=[YOUR-AFFILIATE-TAG]`

Replace:
- `[YOUR-AFFILIATE-TAG]` with your actual tag
- `[BOOK-ASIN-X]` with the correct ASIN

Affiliate disclosure is included near the top of the Resources page.

## Content Updates You Will Want to Make

- App Store links on `download.html` (currently placeholders)
- Pricing section on `download.html`
- Optional: Replace screenshot placeholders with real images when available

## Support Email
All email references use: **PDAQuestionApp@gmail.com**
