"use strict";

const assert = require("node:assert/strict");
const {
  isStickyExcludedPath,
  normalizeStickyPath,
} = require("../assets/js/main.js");

const excludedRoutes = ["download", "privacy", "terms", "terms-california"];

for (const route of excludedRoutes) {
  assert.equal(isStickyExcludedPath(`/${route}.html`), true, `/${route}.html must be excluded`);
  assert.equal(isStickyExcludedPath(`/${route}`), true, `/${route} must be excluded`);
  assert.equal(
    isStickyExcludedPath(`/${route}.html?source=regression#details`),
    true,
    `/${route}.html with query/fragment must be excluded`,
  );
  assert.equal(
    isStickyExcludedPath(`/${route}?source=regression#details`),
    true,
    `/${route} with query/fragment must be excluded`,
  );
}

const allowedRoutes = [
  "/",
  "/index.html",
  "/features.html",
  "/features",
  "/privacy/",
  "/terms/",
  "/download/",
  "/nested/privacy",
  "/not-privacy",
  "/missing.html",
];

for (const route of allowedRoutes) {
  assert.equal(isStickyExcludedPath(route), false, `${route} must remain eligible for the sticky banner`);
}

assert.equal(normalizeStickyPath("/privacy.html"), "/privacy");
assert.equal(normalizeStickyPath("/privacy"), "/privacy");
assert.equal(normalizeStickyPath("/privacy/"), "/privacy/");
assert.equal(normalizeStickyPath("/index.html?preview=1"), "/index");

console.log(`Sticky route regression passed: ${excludedRoutes.length * 4 + allowedRoutes.length + 4} assertions.`);
