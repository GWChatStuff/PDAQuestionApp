# PDA Question Website

This repository contains the public, static website for PDA Question.

- Production website: <https://pdaquestion.com/>
- Repository: [`GWChatStuff/PDAQuestionApp`](https://github.com/GWChatStuff/PDAQuestionApp)
- Hosting: GitHub Pages
- Production source: `main`, published from the repository root
- Support: [PDAQuestionApp@gmail.com](mailto:PDAQuestionApp@gmail.com)

## System boundary

`pdaquestion.com` is the website. The PDA Question iOS app and its backend are a separate system. A website change must never be assumed to change, deploy, configure, or test the app or backend.

The website has no framework or package runtime, application server, website API, authentication, database, form processor, or website OpenAI execution path. It consists of HTML, CSS, JavaScript, images, and standard metadata files served by GitHub Pages.

## Repository layout

- Primary pages are HTML files in the repository root.
- Shared styles are in `assets/css/styles.css`.
- Shared browser behavior is in `assets/js/main.js`.
- Images and icons are in `assets/img/`.
- `CNAME`, `robots.txt`, `sitemap.xml`, and `site.webmanifest` support the production domain and site metadata.
- `.github/workflows/website-integrity.yml` validates pull requests and pushes to `main`; it does not deploy.

Because this is a public repository and `README.md` can be served as a public file, documentation must not contain credentials, private keys, verification values, or private infrastructure details.

## Local preview

No dependency installation or build step is required. From the repository root, run:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open <http://127.0.0.1:8000/>. Opening an HTML file directly is useful for simple inspection, but a local HTTP server more closely matches GitHub Pages behavior.

## Validation

Run the same dependency-free checks used by CI:

```bash
node --check assets/js/main.js
node scripts/test-sticky-routes.js
python3 scripts/validate-site.py
```

Before proposing a change, also inspect the affected pages in light and automatic dark mode, at mobile and desktop widths, and verify keyboard navigation and browser-console output.

## Maintenance and publishing

Make website changes on a feature branch and review them through a pull request into `main`. GitHub Pages publishes the repository root from `main`; do not treat a branch or pull request as a production deployment.

The custom domain is managed through GoDaddy. DNS and GitHub Pages domain settings can change over time, so verify the current authoritative configuration before proposing any domain or hosting change. Do not rely on copied DNS values in old documentation.

Keep canonical URLs, the sitemap, `robots.txt`, App Store identifiers, and the support email consistent when editing public pages. Privacy Policy and Terms changes require a separate review against both the website and the current iOS app/backend behavior.
