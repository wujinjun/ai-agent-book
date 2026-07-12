#!/usr/bin/env node

import puppeteer from "puppeteer";

const [url, output, widthText = "1440", heightText = "1000", fullPageText = "false", selector] =
  process.argv.slice(2);
if (!url || !output) {
  console.error("usage: capture_html.mjs URL OUTPUT [WIDTH] [HEIGHT] [FULL_PAGE]");
  process.exit(2);
}

const browser = await puppeteer.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--allow-file-access-from-files"],
});
const page = await browser.newPage();
await page.setViewport({ width: Number(widthText), height: Number(heightText), deviceScaleFactor: 1 });
await page.goto(url, { waitUntil: "networkidle0" });
if (selector) {
  const element = await page.waitForSelector(selector);
  await element.screenshot({ path: output });
} else {
  await page.screenshot({ path: output, fullPage: fullPageText === "true" });
}
await browser.close();
